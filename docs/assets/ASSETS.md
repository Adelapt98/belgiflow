# Documentation assets and credits

## Original figures and screenshots

`planning-report.svg` and its PNG are generated from the actual default comparison against the cached public Brussels sample. The hub choices are fictional. `pipeline-map.svg` is generated from the actual pipeline catalog. `architecture.svg` describes implemented local components and the target AWS deployment architecture. Original figure layout is covered by the repository MIT license, excluding third-party marks.

`planner-overview.jpg`, `operations-panel.jpg` and `planner-sample.jpg` are actual local browser screenshots. The latter uses a smaller map-selected study area. Neither is a fabricated production customer case. Public geometry attribution appears in the interface and result figure.

Generate the SVGs with `python scripts/render_readme_assets.py` after acquiring the public cache. Convert to PNG with `sh scripts/render_svg_png.sh`, using librsvg and DejaVu Sans fonts. The source generator requires the geographic cache to reproduce its example results.

## Official tool marks

Marks identify tools used by the project, with no endorsement or affiliation implied. They remain the property of their owners and are not relicensed under MIT.

- Dagster logo: [official brand page](https://dagster.io/brand), downloaded from its official company-pages brand assets.
- dbt logo: [official brand guidelines](https://www.getdbt.com/brand-guidelines) and [trademark guidelines](https://www.getdbt.com/dbt-assets/dbt-trademark-guidelines). Source: official linked brand ZIP, `dbt Logos/dbt-logo.png`.
- Apache Spark logo: [official logo](https://spark.apache.org/images/spark-logo-trademark.png). Apache Spark is a trademark of the Apache Software Foundation.
- AWS service icons: [official architecture icon package](https://aws.amazon.com/architecture/icons/), July 2026 release. S3, Redshift, Glue, ECS and CloudWatch icons are retained in `brands/`. Their use does not establish a deployed AWS environment.

To refresh vendor assets, run `python scripts/fetch_visual_assets.py` first, then `python scripts/fetch_tool_logos.py`. The fetch scripts record the official source URLs. Downloaded archives are cached only in ignored `data/` files. Figure generators embed the original marks rather than redrawing them.

## Application dependencies and maps

Leaflet 1.9.4 is vendored from its published npm distribution and retains its BSD 2-Clause license in `src/belgiflow/planner/web/vendor/LICENSE`.

Optional OpenStreetMap tiles retain their visible attribution. Public Overture inputs retain their upstream licenses and attribution obligations. See [source documentation](../SOURCES.md).

`coverage-map.jpg` and `operations-summary.jpg` are focused browser captures of selected interface sections for the README. The map capture retains its attribution, legend and sample provenance. They do not depict the entire workspace.
