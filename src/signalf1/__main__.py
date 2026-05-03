import argparse
import logging

from signalf1 import SignalF1


def main(args=None) -> None:
  parser = argparse.ArgumentParser(prog="signalf1", description="Record F1 live timing telemetry data")
  parser.add_argument("-o", "--output", type=str, default=None, help="Output file path (default: stdout)")
  parser.add_argument("-a", "--append", action="store_true", help="Append to file instead of overwriting")
  parser.add_argument("-t", "--timeout", type=int, default=60, help="Timeout in seconds (0 = no timeout)")
  parser.add_argument("--debug", action="store_true", help="Save raw SignalR messages")
  parsed = parser.parse_args(args)

  logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s: %(message)s")

  file_name = parsed.output

  file_mode = "a" if parsed.append else "w"

  client = SignalF1(file_name=file_name, file_mode=file_mode, debug=parsed.debug, timeout=parsed.timeout)
  client.start()


if __name__ == "__main__":
  main()
