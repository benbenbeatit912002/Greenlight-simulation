# Software and data notices

## Dashboard

Copyright (C) 2026 Hao Yu Liu and contributors.

Except where a file identifies different terms, this repository's original
dashboard and integration source code, tests and documentation are licensed under
the GNU Affero General Public License, version 3 or, at your option, any later
version (AGPL-3.0-or-later). You may use, modify and redistribute them under those
terms. They are provided without warranty; see [LICENSE](LICENSE).

This grant does not replace third-party copyright notices or relicense weather
data, research datasets, dependencies or other third-party material.

## GreenLight and GreenLight-Gym2

The greenhouse model was developed by David Katzin and collaborators.
GreenLight-Gym2 is the implementation by Bart van Laatum and contributors.
Their original copyright and license notices remain applicable. This project
adds the web dashboard, weather-upload handling, greenhouse configuration and
schedule comparisons; it does not claim authorship of the scientific model or
endorsement by its authors. Research references are in [CITATION.md](CITATION.md).

The supported dependency is [gl-gym 0.3.2](https://pypi.org/project/gl-gym/0.3.2/).
Its distribution declares AGPL-3.0-or-later and includes the full AGPL v3 license.
The model is installed as a dependency, not copied into this repository.
Separate installation does not waive its license obligations.

- [Upstream repository](https://github.com/BartvLaatum/GreenLight-Gym2)
- [Source archive for gl-gym 0.3.2](https://files.pythonhosted.org/packages/c4/22/973120ed1ad85a64d66aed793f0e459b622522f38f76bab8da7db9ab7a71/gl_gym-0.3.2.tar.gz)
- Source archive SHA-256: `9bffa2c841b6a75d3aa87ec2a62b4ba32b52f9174701d8ebf7c4e6b9bc810a7a`

The archive and hash match [uv.lock](uv.lock). A different model version or a
custom checkout needs its own source and license review.

## Other dependencies

These direct dependencies are installed separately, not vendored here:

| Package | Locked version | License |
| --- | --- | --- |
| [openpyxl](https://pypi.org/project/openpyxl/3.1.5/) | 3.1.5 | MIT |
| [defusedxml](https://pypi.org/project/defusedxml/0.7.1/) | 0.7.1 | Python Software Foundation License |
| [Prettier](https://github.com/prettier/prettier/tree/3.8.1) (development only) | 3.8.1 | MIT |

The model also brings its own dependencies. The complete resolved package
versions are in [uv.lock](uv.lock) and [package-lock.json](package-lock.json).
Their own license files and notices remain authoritative. If you bundle an
environment or executable for others, include the applicable notices and meet
each dependency's source-distribution requirements; this summary is not a
replacement for those files or a complete dependency-license inventory.

## Weather and research data

The Amsterdam, Almería and Taipei Excel examples use NASA POWER data. Preserve
their accompanying `.source.json` records and NASA acknowledgement. See the
[example sources and conversions](docs/public-weather-examples.md),
[weather collection notes](data/weather/README.md) and
[NASA referencing guidance](https://power.larc.nasa.gov/docs/referencing/).
This project's software license does not assign a new license to NASA data.

The Amsterdam weather installed with gl-gym is a separate upstream dataset, not
the NASA Excel example. Check its original provenance and applicable data terms
before redistributing it independently; the package's software-license label
alone does not establish those rights.

Downloaded WUR datasets, user uploads and research results are not licensed by
this notice. Follow each dataset's own terms and do not publish private inputs.

## Sharing or hosting a modified version

Keep the applicable notices, identify your changes and dates, and provide the
corresponding source as required by the license. Installation instructions are
in [the setup guide](docs/installation.md).

The dashboard's Source code link points to
[this repository](https://github.com/benbenbeatit912002/Greenlight-simulation).
If you distribute or host a modified version, publish the source that matches
that version, including required build/install scripts and covered dependencies.
For remote users of a covered modified version, provide a prominent, no-charge
source-download link as required by AGPL section 13. Update the dashboard link
to your matching source release; a link to an unrelated or older upstream
version is not sufficient. Do not expose your whole checkout, private data or
credentials through the web server.
