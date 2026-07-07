# Environment Dependency Audit

Status: `pass`

This audit records the local Python/platform snapshot, required Python packages, output-format packages, bounded-simulator packages, test package, and PDF/system tools needed by the current non-hardware pack.

| metric | value |
|---|---:|
| rows checked | 16 |
| required entries | 14 |
| required failures | 0 |
| optional missing | 0 |

## Environment Snapshot

| field | value |
|---|---|
| python executable | `<USER_HOME>\AppData\Local\Programs\Python\Python310\python.exe` |
| python version | `3.10.11` |
| platform | `Windows-10-10.0.26200-SP0` |
| machine | `AMD64` |
| implementation | `CPython` |
| required python | `>=3.10` |

## Dependency Rows

| kind           | name       | import_name   | tier                    | required   | installed   | version                           | declared_in_pyproject   | path                                                                  | status   | reason                                             |
|:---------------|:-----------|:--------------|:------------------------|:-----------|:------------|:----------------------------------|:------------------------|:----------------------------------------------------------------------|:---------|:---------------------------------------------------|
| python_package | numpy      | numpy         | core                    | True       | True        | 1.26.4                            | True                    |                                                                       | pass     | analytic simulation, models, and statistics        |
| python_package | pandas     | pandas        | core                    | True       | True        | 2.3.3                             | True                    |                                                                       | pass     | tables, reports, CSV/Parquet IO                    |
| python_package | matplotlib | matplotlib    | core                    | True       | True        | 3.10.8                            | True                    |                                                                       | pass     | generated figures                                  |
| python_package | pillow     | PIL           | core                    | True       | True        | 12.1.0                            | True                    |                                                                       | pass     | GIF/video and image validation                     |
| python_package | pypdf      | pypdf         | core                    | True       | True        | 6.9.2                             | True                    |                                                                       | pass     | PDF structure verification                         |
| python_package | pyyaml     | yaml          | core                    | True       | True        | 6.0.3                             | True                    |                                                                       | pass     | YAML config compatibility                          |
| python_package | pyarrow    | pyarrow       | output_format           | True       | True        | 23.0.0                            | True                    |                                                                       | pass     | pandas Parquet output                              |
| python_package | tabulate   | tabulate      | output_format           | True       | True        | 0.10.0                            | True                    |                                                                       | pass     | pandas markdown table output                       |
| python_package | pytest     | pytest        | test                    | True       | True        | 9.0.2                             | True                    |                                                                       | pass     | documented test command                            |
| python_package | mujoco     | mujoco        | bounded_simulator       | True       | True        | 3.9.0                             | True                    |                                                                       | pass     | bounded MuJoCo probe tier                          |
| python_package | mani-skill | mani_skill    | bounded_simulator       | True       | True        | 3.0.1                             | True                    |                                                                       | pass     | bounded ManiSkill probe tier                       |
| python_package | gymnasium  | gymnasium     | bounded_simulator       | True       | True        | 1.2.3                             | True                    |                                                                       | pass     | ManiSkill environment wrapper                      |
| system_tool    | pdflatex   |               | paper_build             | True       | True        | MiKTeX-pdfTeX 4.23 (MiKTeX 25.12) |                         | <USER_HOME>\.local\bin\pdflatex.CMD                                   | pass     | clean PDF build from paper/main.tex                |
| system_tool    | bibtex     |               | paper_build             | True       | True        | MiKTeX-BibTeX 4.2 (MiKTeX 25.12)  |                         | <USER_HOME>\AppData\Local\Programs\MiKTeX\miktex\bin\x64\bibtex.EXE   | pass     | clean bibliography build from paper/references.bib |
| system_tool    | pdftoppm   |               | pdf_visual_validation   | False      | True        | pdftoppm version 24.04.0          |                         | <USER_HOME>\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdftoppm.EXE | pass     | optional rendered-page inspection                  |
| system_tool    | pdfinfo    |               | pdf_metadata_validation | False      | True        | pdfinfo version 24.04.0           |                         | <USER_HOME>\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdfinfo.EXE  | pass     | optional PDF metadata inspection                   |
