name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Test (Python ${{ matrix.python-version }}, ${{ matrix.os }})
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.9', '3.10', '3.11', '3.12', '3.13']
        exclude:
          - os: windows-latest
            python-version: '3.9'

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
          cache-dependency-path: |
            requirements.txt
            setup.py

      - name: Install Linux dependencies
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y build-essential gcc g++ python3-dev xvfb

      - name: Install macOS dependencies
        if: runner.os == 'macOS'
        run: brew install gcc llvm python3

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-qt pytest-xdist pytest-timeout

      - name: Build C++ extension
        run: python setup.py build_ext --inplace

      - name: Run unit tests
        timeout-minutes: 10
        run: pytest tests/ -v --cov=src --cov-report=xml --cov-report=term

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          flags: ${{ matrix.os }},py${{ matrix.python-version }}
          name: codecov-${{ matrix.os }}-py${{ matrix.python-version }}
          fail_ci_if_error: false
          token: ${{ secrets.CODECOV_TOKEN }}

      - name: Upload test logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: logs-${{ matrix.os }}-py${{ matrix.python-version }}
          path: |
            compilador.log
            test-*.log
            pytest*.log
          retention-days: 7

  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install linting tools
        run: |
          pip install flake8 black isort autoflake mypy pylint
      - name: Auto-format
        run: |
          isort src/ --profile black --line-length 100
          black src/ --line-length 100
          autoflake --in-place --remove-all-unused-imports --remove-unused-variables --recursive src/
      - name: Run flake8
        run: flake8 src/ --max-line-length=100 --count --statistics
      - name: Run mypy
        run: mypy src/ --ignore-missing-imports --no-strict-optional || true

  build-test:
    name: Build Test (${{ matrix.os }})
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyinstaller
      - name: Build C++ extension
        run: python setup.py build_ext --inplace
      - name: Test PyInstaller build
        shell: bash
        run: |
          pyinstaller --onefile --windowed --name compilador src/main.py
          if [ "$RUNNER_OS" == "Windows" ]; then
            ls -la dist/
          else
            ls -la dist/
          fi
      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: build-test-${{ matrix.os }}
          path: dist/
          retention-days: 7