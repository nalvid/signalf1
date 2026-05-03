# SignalF1

SignalF1 is a Python package for recording and processing F1 live timing telemetry data.

## Installation

Install the latest version from the GitHub main branch:

```shell
python -m pip install git+https://github.com/4e1e0603/signalf1.git@main#egg=signalf1
```

To install a specific tagged version:

```shell
python -m pip install git+https://github.com/4e1e0603/signalf1.git@<TAG>#egg=signalf1
```

## Usage

Run the command line script:

```shell
signalf1 <arguments>
```

By default, telemetry data is written to stdout and application logs go to stderr.
Use `-o <path>` if you want to persist telemetry data to a file.

To run the package module directly:

```shell
python -m signalf1 <arguments>
```

## Development

Create a virtual environment (Python 3.13 recommended):

```shell
uv venv -p 3.13
```

Install dependencies in editable mode:

```shell
uv pip install -e . -r requirements.txt
```

## Resources

- <https://blog.3d-logic.com/2015/03/29/signalr-on-the-wire-an-informal-description-of-the-signalr-protocol/>
- <https://www.formula1.com>
- <https://www.bbc.com/sport/formula1>
- <https://en.wikipedia.org/wiki/2023_Formula_One_World_Championship>
- <https://twitter.com/f1dataanalysis>
- <https://github.com/f1db/f1db>
