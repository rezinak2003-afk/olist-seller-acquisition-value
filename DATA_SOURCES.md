# Data sources, attribution and reproducibility

| Dataset | Official source | Intended use | Kaggle licence shown on source page |
|---|---|---|---|
| Olist Marketing Funnel | https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist | Qualified leads and closed deals | CC BY-NC-SA 4.0 |
| Olist Brazilian E-Commerce Public Dataset | https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce | Orders, order items, reviews, payments | CC BY-NC-SA 4.0 |
| Original Olist marketing challenge | https://github.com/olist/work-at-olist-marketing | Business context | Repository context only; not the licence for either dataset |

**Attribution:** Olist, *Marketing Funnel by Olist* and *Brazilian E-Commerce Public Dataset by Olist*, published on Kaggle. Retain a citation to both original dataset pages when publishing derived analyses.

**Licence note:** both Kaggle dataset pages identify the datasets as **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**. The attribution, non-commercial and share-alike conditions apply to the dataset material and adaptations. The project code has a separate MIT licence; that does not relicense the Olist data. This is a portfolio/research project, not legal advice. Obtain permission or qualified advice before commercial use or redistribution of data or adaptations.

**Distribution rule:** raw Olist CSVs and downloaded ZIPs are excluded from Git. Re-download them from the official Kaggle pages and place the pipeline inputs in `data/raw/` (and optional payments in `data/reference/`). The pipeline creates `source_manifest.csv` with byte sizes and SHA-256 checksums. The retrieval date is marked `not_recorded` unless you set it yourself. Do not publish raw CSVs in this repository.
