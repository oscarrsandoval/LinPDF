#!/usr/bin/env python3
import sys
from linpdf.app import Application


def main():
    app = Application(sys.argv)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
