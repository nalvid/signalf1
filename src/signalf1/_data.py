"""
Data object for livetiming data
"""

import ast
import datetime
import json
import logging
import warnings
from datetime import timedelta
from functools import reduce

_logger = logging.getLogger(__name__)


def recursive_dict_get(d: dict, *keys: str, default_none: bool = False):
  """Recursive dict get. Can take an arbitrary number of keys and returns an
  empty dict if any key does not exist.
  https://stackoverflow.com/a/28225747"""
  ret = reduce(lambda c, k: c.get(k, {}), keys, d)
  if default_none and ret == {}:
    return None
  else:
    return ret


def to_timedelta(x: str | datetime.timedelta) -> datetime.timedelta | None:
  """Fast timedelta object creation from a time string

  Permissible string formats:

      For example: `13:24:46.320215` with:

          - optional hours and minutes
          - optional microseconds and milliseconds with
            arbitrary precision (1 to 6 digits)

      Examples of valid formats:

          - `24.3564` (seconds + milli/microseconds)
          - `36:54` (minutes + seconds)
          - `8:45:46` (hours, minutes, seconds)

  Args:
      x: timestamp
  """
  # this is faster than using pd.timedelta on a string
  if isinstance(x, str) and len(x):
    try:
      hours, minutes = 0, 0
      if len(hms := x.split(":")) == 3:
        hours, minutes, seconds = hms
      elif len(hms) == 2:
        minutes, seconds = hms
      else:
        seconds = hms[0]

      if "." in seconds:
        seconds, msus = seconds.split(".")
        if len(msus) < 6:
          msus = msus + "0" * (6 - len(msus))
        elif len(msus) > 6:
          msus = msus[0:6]
      else:
        msus = 0

      return datetime.timedelta(
        hours=int(hours),
        minutes=int(minutes),
        seconds=int(seconds),
        microseconds=int(msus),
      )

    except Exception as exc:
      _logger.debug(f"Failed to parse timedelta string '{x}'", exc_info=exc)
      return None

  elif isinstance(x, datetime.timedelta):
    return x

  else:
    return None


def to_datetime(x: str | datetime.datetime) -> datetime.datetime | None:
  """Fast datetime object creation from a date string.

  Permissible string formats:

      For example '2020-12-13T13:27:15.320000Z' with:

          - optional milliseconds and microseconds with
            arbitrary precision (1 to 6 digits)
          - with optional trailing letter 'Z'

      Examples of valid formats:

          - `2020-12-13T13:27:15.320000`
          - `2020-12-13T13:27:15.32Z`
          - `2020-12-13T13:27:15`

  Args:
      x: timestamp
  """
  if isinstance(x, str) and x:
    try:
      date, time = x.strip("Z").split("T")
      year, month, day = date.split("-")
      hours, minutes, seconds = time.split(":")
      if "." in seconds:
        seconds, msus = seconds.split(".")
        if len(msus) < 6:
          msus = msus + "0" * (6 - len(msus))
        elif len(msus) > 6:
          msus = msus[0:6]
      else:
        msus = 0

      return datetime.datetime(
        int(year),
        int(month),
        int(day),
        int(hours),
        int(minutes),
        int(seconds),
        int(msus),
      )

    except Exception as exc:
      _logger.debug(f"Failed to parse datetime string '{x}'", exc_info=exc)
      return None

  elif isinstance(x, datetime.datetime):
    return x

  else:
    return None


_track_status_mapping = {
  "AllClear": "1",
  "Yellow": "2",
  "SCDeployed": "4",
  "Red": "5",
  "VSCDeployed": "6",
  "VSCEnding": "7",
}


class LiveTimingData:
  """Live timing data object for using saved livetiming data as data source.

  This object is created from data that was recorded using
  :class:`signalf1.SignalF1`. It can be used to load saved telemetry
  recordings for downstream analysis.

  Usually you will only instantiate this function and pass it to
  other functions.

  See :mod:`signalf1.extractor` for higher-level log analysis helpers.

  If you want to load data from multiple files you can simply pass multiple
  filenames::

      livedata = LiveTimingData('file1.txt', 'file2.txt', 'file3.txt')

  The files need to be in chronological order but may overlap. I.e. if the
  last five minutes of file1 are the same as the first 5 minutes of file2
  this will be recognized while loading the data. No duplicate data will
  be loaded.

  Args:
      *files (str): One or multiple file names
  """

  def __init__(self, *files, **kwargs):
    # file names
    self.files = files
    # parsed data
    self.data = {}
    # number of json errors
    self.errorcount = 0
    # flag for automatic data loading on first access
    self._files_read = False
    # date when session was started
    self._start_date = None

    if "remove_duplicates" in kwargs:
      warnings.warn(
        "The argument `remove_duplicates` is no longer "
        "available. Duplicates caused by overlapping files "
        "will now always be removed."
      )

  def load(self):
    """
    Read all files, parse the data and store it by category.

    Should usually not be called manually. This is called
    automatically the first time :meth:`get`, :meth:`has`
    or :meth:`list_categories` are called.
    """
    _logger.info("Reading live timing data from recording. This may take a bit.")

    is_first = True
    _files = [*self.files, None]
    current_data, next_data = None, None

    # We always need the current and next file loaded, so we can detect
    # where they overlap. The "next" file then becomes the "current" file
    # and the next "next" file is read.
    for next_file in _files:
      # make the previous "next" file the "current" file
      current_data = next_data

      if next_file is None:
        # reached the end, there is no subsequent data anymore
        next_data = None
      else:
        # read a new file as next file
        with open(next_file) as fobj:
          next_data = fobj.readlines()

      if current_data is None:
        # there is no "current" file yet (i.e. first iteration),
        # skip ahead once right away to read one more file
        continue

      overlap_length = self._find_overlap_length(current_data, next_data)
      self._load_single_file(current_data, is_first_file=is_first, overlap_length=overlap_length)
      is_first = False

    # set flag that all files have been read
    self._files_read = True

  def _load_single_file(self, data, *, is_first_file, overlap_length=0):
    # parse its content and add it to the already loaded
    # data (if there is data already)

    # try to find the correct start date (only if this is the first file)
    if is_first_file:
      self._try_set_correct_start_date(data)

    if overlap_length:
      data = data[:-overlap_length]

    for line in data:
      self._parse_line(line)

    # first file was loaded, others are appended if any more are loaded
    self._previous_files = True

  def _find_overlap_length(self, current_data, next_data):
    if not current_data or not next_data:
      return 0

    max_overlap = min(len(current_data), len(next_data))
    for overlap_length in range(max_overlap, 0, -1):
      if current_data[-overlap_length:] == next_data[:overlap_length]:
        return overlap_length

    return 0

  def _parse_line(self, elem):
    # parse a single line of data

    # load the three parts of each data element
    try:
      cat, msg, dt_str = self._parse_record(elem)
    except ValueError:
      self.errorcount += 1
      return

    # convert string to datetime
    dt = to_datetime(dt_str)
    if dt is None:
      self.errorcount += 1
      return

    # if no start date could be determined beforehand, simply use the
    # first timestamp as we need to have some date as start date;
    # convert timestamp to timedelta (SessionTime) base on start date
    if self._start_date is None:
      self._start_date = dt
      td = timedelta(seconds=0)
    else:
      td = dt - self._start_date

    self._add_to_category(cat, [td, msg])

  def _parse_record(self, elem):
    payload = elem.strip()
    if not payload:
      raise ValueError("Empty record")

    if payload[0] not in "[{":
      for marker in (",[", ",{"):
        marker_index = payload.find(marker)
        if marker_index != -1:
          payload = payload[marker_index + 1 :]
          break

    try:
      record = json.loads(payload)
    except json.JSONDecodeError:
      try:
        record = ast.literal_eval(payload)
      except (SyntaxError, ValueError) as exc:
        raise ValueError("Invalid record") from exc

    if not isinstance(record, (list, tuple)) or len(record) != 3:
      raise ValueError("Unexpected record shape")

    return record

  def _add_to_category(self, cat, entry):
    if cat not in self.data:
      self.data[cat] = [
        entry,
      ]
    else:
      self.data[cat].append(entry)

  def _try_set_correct_start_date(self, data):
    # skim content to find 'Started' session status without actually
    # decoding each line to save time
    for elem in data:
      if "SessionStatus" in elem and "Started" in elem:
        break
    else:
      # didn't find 'Started'
      _logger.error("Error while trying to set correct session start date!")
      return

    # decode matching line
    try:
      cat, msg, dt = self._parse_record(elem)
    except ValueError:
      _logger.error("Error while trying to set correct session start date!")
      return

    # find correct entry in series
    try:
      for entry in msg["StatusSeries"]:
        status = recursive_dict_get(entry, "SessionStatus")
        if status == "Started":
          try:
            self._start_date = to_datetime(entry["Utc"])
          except (KeyError, ValueError, TypeError):
            self.errorcount += 1
            _logger.error("Error while trying to set correct session start date!")
            return
    except AttributeError:
      for entry in msg["StatusSeries"].values():
        status = entry.get("SessionStatus", None)
        if status == "Started":
          try:
            self._start_date = to_datetime(entry["Utc"])
          except (KeyError, ValueError, TypeError):
            self.errorcount += 1
            _logger.error("Error while trying to set correct session start date!")
            return

  def get(self, name):
    """
    Return data for category name.

    Will load data on first call, this will take a bit.

    Args:
        name (str): name of the category
    """
    if not self._files_read:
      self.load()
    return self.data[name]

  def has(self, name):
    """
    Check if data for a category name exists.

    Will load data on first call, this will take a bit.

    Args:
        name (str): name of the category
    """
    if not self._files_read:
      self.load()
    return name in self.data.keys()

  def list_categories(self):
    """
    List all available data categories.

    Will load data on first call, this will take a bit.

    Returns:
        list of category names
    """
    if not self._files_read:
      self.load()
    return list(self.data.keys())
