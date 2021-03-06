
As of March 2018, the archive runs Pig version 0.12.0, via CDH5.0.1 (Cloudera
Distribution).

"Local mode" unit tests in this folder run with Pig version 0.17.0 (controlled
by `fetch_deps.sh`) due to [dependency/jar issues][pig-bug] in local mode of
0.12.0.

[pig-bug]: https://issues.apache.org/jira/browse/PIG-3530

## Development and Testing

To run tests, you need Java installed and `JAVA_HOME` configured.

Fetch dependencies (including pig) from top-level directory:

    ./fetch_hadoop.sh

Write `.pig` scripts in this directory, and add a python wrapper test to
`./tests/` when done.  Test vector files (input/output) can go in
`./tests/files/`.

Run the tests with:

    pipenv run pytest

Could also, in theory, use a docker image ([local-pig][]), but it's pretty easy
to just download.

[local-pig]: https://hub.docker.com/r/chalimartines/local-pig

## Run in Production

    pig -param INPUT="/user/bnewbold/pdfs/global-20171227034923" \
        -param OUTPUT="/user/bnewbold/pdfs/gwb-pdf-20171227034923-surt-filter" \
        filter-cdx-paper-pdfs.pig
