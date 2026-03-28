# Reference Style Memory: Nature / npj / Science V1

This note fixes the default reference-writing policy for the manuscript and records the journal-style rules that should guide future revisions.

## 1. Default decision for this project

The target manuscript should use **Nature / npj reference style** throughout.

Reason:
- the current target venue is `npj Artificial Intelligence`
- npj journals explicitly use standard Nature referencing style
- mixing Nature/npj and Science-style references in one manuscript is not acceptable

Therefore:
- `Nature / npj` is the production style
- `Science` is kept only as a comparative style reference for learning and tone, not as the formatting standard for this manuscript

## 2. Official Nature / npj reference habits to preserve

Based on Nature and npj author guidance:

1. References are **numbered sequentially** in the order of first appearance.
2. The same number is reused when the same source is cited again.
3. References are cited in text as **numbers**, and Nature commonly uses **superscript citation style** in final form.
4. Only **one publication per reference number**.
5. Only published works, accepted works, recognized preprints, patents, and citable datasets should appear in the reference list.
6. URLs for ordinary websites should usually stay in the text, not be treated like journal references, unless the item is a formal citable source.
7. **Article titles are required** in the reference list.
8. Author names should be formatted as:
   - `Surname, Initials.`
9. Nature style includes **all authors unless there are more than five**; if more than five, give the first author followed by `et al.`
10. Journal titles are written in the **journal's standard abbreviation or official form used by the journal style**, not in ad hoc abbreviations.
11. Reference lists should be consistent in punctuation, year placement, volume, and page/article-number format.

## 3. What Nature / npj references should look like

### Journal article

Preferred pattern:

`Surname, Initials. Title of article. Journal Title volume, page-range or article number (year).`

Example pattern:

`Li, B. & Zhao, C. Self-reflection enhances large language models towards substantial academic response. npj Artif. Intell. 1, 45 (2025).`

### Preprint

Preferred pattern:

`Surname, Initials. Title. arXiv preprint arXiv:xxxx.xxxxx (year).`

### Dataset / scientific resource paper

Preferred pattern:

`Surname, Initials. Title. Journal Title volume, page-range or article number (year).`

If citing the resource itself via its paper, cite the paper, not just the website.

## 4. Science-style habits worth learning, but not adopting as manuscript default

Science papers also use a numbered citation-sequence style, but their reference presentation is typically more compact and often relies on journal abbreviations in a way that feels slightly different in texture from Nature.

Useful takeaways from Science-like style:
- keep references compact
- use consistent abbreviation practice
- make every citation do argumentative work
- avoid bloated, redundant bibliographies

But do **not** switch the manuscript into an in-between hybrid style.

## 5. Practical rules for this manuscript

From now on, every reference revision should follow these rules:

1. Use **numbered references only**.
2. Do not mix author-year citations with numbered citations.
3. Include article titles for journal papers.
4. Normalize author names to `Surname, Initials.`
5. Use `et al.` only when the author list exceeds the Nature/npj threshold.
6. **Prefer peer-reviewed journal or conference versions over arXiv whenever they exist.**
7. Use arXiv only when no formal published version is available or when the preprint itself is the canonical source being discussed.
8. Prefer citing formal papers for CODATA, NIST WebBook, PubChem, ChEBI, and Materials Project rather than raw URLs.
9. When discussing related work, cite the closest mechanism papers in the Introduction and Discussion, not only in the bibliography.
10. For this manuscript type, keep the draft in the range of roughly **12--20 carefully used references** at minimum, and expand only when the argument genuinely needs it.

## 6. Common mistakes to avoid

- Do not leave references in informal LaTeX note style.
- Do not omit article titles.
- Do not default to arXiv if a formal publication already exists.
- Do not cite a website when a canonical paper exists.
- Do not mix full journal names in some entries and abbreviated names in others unless the target style explicitly requires one or the other and the list is globally consistent.
- Do not let the bibliography become richer than the in-text citation logic.
- Do not use references as a dumping ground for uncited background reading.

## 7. Default rewrite checklist for future bibliography cleanup

Whenever the manuscript bibliography is revised, apply this checklist:

1. Is the reference list fully numbered and sequential?
2. Does every entry have a title?
3. Are author names normalized?
4. Have arXiv citations been replaced by formal publications wherever possible?
5. Are related-work citations present in Introduction, Methods, and Discussion where needed?
6. Are scientific data sources cited via formal resource papers?
7. Is the whole list internally consistent in punctuation and year placement?

## 8. Permanent memory decision

For this project, the default citation and bibliography policy is:

**Write like Nature / npj. Learn from Science, but do not format like Science unless the target journal changes.**

Additional standing rule:

**Use arXiv sparingly and only when a stronger citable version is unavailable.**
