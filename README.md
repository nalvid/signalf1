# SignalF1

SignalF1 is a Python package for working with F1 telemetry data, including tools for command-line processing and running a server.

## Installation

Install the latest version from the GitHub main branch:

```shell
python -m pip install git+https://github.com/4e1e0603/signalf1.git@main#egg=signalf1&subdirectory=signal1
```

To install a specific tagged version:

```shell
python -m pip install git+https://github.com/4e1e0603/signalf1.git@<TAG>#egg=signalf1&subdirectory=signal1
```

## Usage

Run the command line script:

```shell
signalf1 <arguments>
```

Or start the server:

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
