"""
Data object for livetiming data
"""

import json
import logging
import warnings
from datetime import timedelta
import datetime
import warnings
from functools import reduce
from typing import (
    Optional,
    Union
)

_logger = logging.getLogger(__name__)
import numpy as np
import pandas as pd

def delta_time(
        reference_lap: "fastf1.core.Lap",
        compare_lap: "fastf1.core.Lap"
) -> tuple[pd.Series, "fastf1.core.Telemetry", "fastf1.core.Telemetry"]:
    """Calculates the delta time of a given lap, along the 'Distance' axis
    of the reference lap.

    .. deprecated:: 3.0.0

    .. warning:: This function should no longer be considered as a stable part
        of the API. Due to the reasons given below, this function will be
        modified or removed at a future point.

    .. warning:: This is a nice gimmick but not actually very accurate which
        is an inherent problem from the way this is calculated currently
        (There may not be a better way though). In comparison with the sector
        times and the differences that can be calculated from these, there are
        notable differences! You should always verify the result against
        sector time differences or find a different way for verification.

    Here is an example that compares the quickest laps of Leclerc and
    Hamilton from Bahrain 2021 Qualifying:

    .. plot::
        :include-source:

        import fastf1 as ff1
        from fastf1 import plotting
        from fastf1 import utils
        from matplotlib import pyplot as plt

        plotting.setup_mpl(misc_mpl_mods=False, color_scheme='fastf1')

        session = ff1.get_session(2021, 'Emilia Romagna', 'Q')
        session.load()
        lec = session.laps.pick_driver('LEC').pick_fastest()
        ham = session.laps.pick_driver('HAM').pick_fastest()

        delta_time, ref_tel, compare_tel = utils.delta_time(ham, lec)
        # ham is reference, lec is compared

        fig, ax = plt.subplots()
        # use telemetry returned by .delta_time for best accuracy,
        # this ensures the same applied interpolation and resampling
        ax.plot(ref_tel['Distance'], ref_tel['Speed'],
                color=plotting.get_team_color(ham['Team'], session))
        ax.plot(compare_tel['Distance'], compare_tel['Speed'],
                color=plotting.get_team_color(lec['Team'], session))

        twin = ax.twinx()
        twin.plot(ref_tel['Distance'], delta_time, '--', color='white')
        twin.set_ylabel("<-- Lec ahead | Ham ahead -->")
        plt.show()

    Args:
        reference_lap: The lap taken as reference
        compare_lap: The lap to compare

    Returns:
        A tuple containing

        - pd.Series of type `float64` with the delta in seconds.
        - :class:`~fastf1.core.Telemetry` for the reference lap
        - :class:`~fastf1.core.Telemetry` for the comparison lap

        Use the return telemetry for plotting to make sure you have
        telemetry data that was created with the same interpolation and
        resampling options!
    """
    warnings.warn("`utils.delta_time` is considered deprecated and will"
                  "be modified or removed in a future release because it has"
                  "a tendency to give inaccurate results.",
                  FutureWarning)

    ref = reference_lap.get_car_data(interpolate_edges=True).add_distance()
    comp = compare_lap.get_car_data(interpolate_edges=True).add_distance()

    def mini_pro(stream):
        # Ensure that all samples are interpolated
        dstream_start = stream[1] - stream[0]
        dstream_end = stream[-1] - stream[-2]
        return np.concatenate(
            [[stream[0] - dstream_start], stream, [stream[-1] + dstream_end]]
        )

    ltime = mini_pro(comp['Time'].dt.total_seconds().to_numpy())
    multiplier = ref.Distance.iat[-1]/comp.Distance.iat[-1]
    ldistance = mini_pro(comp['Distance'].to_numpy())*multiplier
    lap_time = np.interp(ref['Distance'], ldistance, ltime)

    delta = lap_time - ref['Time'].dt.total_seconds()

    return delta, ref, comp


def recursive_dict_get(d: dict, *keys: str, default_none: bool = False):
    """Recursive dict get. Can take an arbitrary number of keys and returns an
    empty dict if any key does not exist.
    https://stackoverflow.com/a/28225747"""
    ret = reduce(lambda c, k: c.get(k, {}), keys, d)
    if default_none and ret == {}:
        return None
    else:
        return ret


def to_timedelta(x: Union[str, datetime.timedelta]) \
        -> Optional[datetime.timedelta]:
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
            if len(hms := x.split(':')) == 3:
                hours, minutes, seconds = hms
            elif len(hms) == 2:
                minutes, seconds = hms
            else:
                seconds = hms[0]

            if '.' in seconds:
                seconds, msus = seconds.split('.')
                if len(msus) < 6:
                    msus = msus + '0' * (6 - len(msus))
                elif len(msus) > 6:
                    msus = msus[0:6]
            else:
                msus = 0

            return datetime.timedelta(
                hours=int(hours), minutes=int(minutes),
                seconds=int(seconds), microseconds=int(msus)
            )

        except Exception as exc:
            _logger.debug(f"Failed to parse timedelta string '{x}'",
                          exc_info=exc)
            return None

    elif isinstance(x, datetime.timedelta):
        return x

    else:
        return None


def to_datetime(x: Union[str, datetime.datetime]) \
        -> Optional[datetime.datetime]:
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
            date, time = x.strip('Z').split('T')
            year, month, day = date.split('-')
            hours, minutes, seconds = time.split(':')
            if '.' in seconds:
                seconds, msus = seconds.split('.')
                if len(msus) < 6:
                    msus = msus + '0' * (6 - len(msus))
                elif len(msus) > 6:
                    msus = msus[0:6]
            else:
                msus = 0

            return datetime.datetime(
                int(year), int(month), int(day), int(hours),
                int(minutes), int(seconds), int(msus)
            )

        except Exception as exc:
            _logger.debug(f"Failed to parse datetime string '{x}'",
                          exc_info=exc)
            return None

    elif isinstance(x, datetime.datetime):
        return x

    else:
        return None



_track_status_mapping = {
    'AllClear': '1',
    'Yellow': '2',
    'SCDeployed': '4',
    'Red': '5',
    'VSCDeployed': '6',
    'VSCEnding': '7'
}


class LiveTimingData:
    """Live timing data object for using saved livetiming data as data source.

    This object is created from data that was recorded using
    :class:`~fastf1.livetiming.client.SignalRClient`. It can be passed to
    various api calling functions using the ``livedata`` keyword.

    Usually you will only instantiate this function and pass it to
    other functions.

    See :mod:`fastf1.livetiming` for a usage example.

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
        self.data = dict()
        # number of json errors
        self.errorcount = 0
        # flag for automatic data loading on first access
        self._files_read = False
        # date when session was started
        self._start_date = None

        if 'remove_duplicates' in kwargs:
            warnings.warn("The argument `remove_duplicates` is no longer "
                          "available. Duplicates caused by overlapping files "
                          "will now always be removed.")

    def load(self):
        """
        Read all files, parse the data and store it by category.

        Should usually not be called manually. This is called
        automatically the first time :meth:`get`, :meth:`has`
        or :meth:`list_categories` are called.
        """
        _logger.info("Reading live timing data from recording. "
                     "This may take a bit.")

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

            next_line = next_data[0] if next_data else None

            self._load_single_file(current_data,
                                   is_first_file=is_first,
                                   next_line=next_line)
            is_first = False

        # set flag that all files have been read
        self._files_read = True

    def _load_single_file(self, data, *, is_first_file, next_line):
        # parse its content and add it to the already loaded
        # data (if there is data already)

        # try to find the correct start date (only if this is the first file)
        if is_first_file:
            self._try_set_correct_start_date(data)

        for line in data:
            if line == next_line:
                break
            self._parse_line(line)

        # first file was loaded, others are appended if any more are loaded
        self._previous_files = True

    def _parse_line(self, elem):
        # parse a single line of data

        # load the three parts of each data element
        elem = self._fix_json(elem)
        try:
            cat, msg, dt_str = json.loads(elem)
        except (json.JSONDecodeError, ValueError):
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

    def _fix_json(self, elem):
        # fix F1's not json compliant data
        elem = elem.replace("'", '"') \
            .replace('True', 'true') \
            .replace('False', 'false')
        return elem

    def _add_to_category(self, cat, entry):
        if cat not in self.data:
            self.data[cat] = [entry, ]
        else:
            self.data[cat].append(entry)

    def _try_set_correct_start_date(self, data):
        # skim content to find 'Started' session status without actually
        # decoding each line to save time
        for elem in data:
            if 'SessionStatus' in elem and 'Started' in elem:
                break
        else:
            # didn't find 'Started'
            _logger.error("Error while trying to set correct "
                          "session start date!")
            return

        # decode matching line
        elem = self._fix_json(elem)
        try:
            cat, msg, dt = json.loads(elem)
        except (json.JSONDecodeError, ValueError):
            _logger.error("Error while trying to set correct "
                          "session start date!")
            return

        # find correct entry in series
        try:
            for entry in msg['StatusSeries']:
                status = recursive_dict_get(entry, 'SessionStatus')
                if status == 'Started':
                    try:
                        self._start_date = to_datetime(entry['Utc'])
                    except (KeyError, ValueError, TypeError):
                        self.errorcount += 1
                        _logger.error("Error while trying to set correct "
                                      "session start date!")
                        return
        except AttributeError:
            for entry in msg['StatusSeries'].values():
                status = entry.get('SessionStatus', None)
                if status == 'Started':
                    try:
                        self._start_date = to_datetime(entry['Utc'])
                    except (KeyError, ValueError, TypeError):
                        self.errorcount += 1
                        _logger.error("Error while trying to set correct "
                                      "session start date!")
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
