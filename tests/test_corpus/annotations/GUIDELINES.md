# Annotation Guidelines: NER Benchmark Corpus

**Status:** APPROVED by Lionel on 2026-10-02 (STOP A, Story 10.1). Reviewed draft: commit `e7835a3`, sha256 `57ceba37a60014c900637c441c95db3b4fc8e3c059821486698b604d101fe37e`. Part A was approved as drafted. Part B records his answers; three of them changed the proposed default (Q3, Q5, Q14). The decision record is at the end of this file. Amendments A1–A6 and A7 were decided by Lionel on 2026-10-03 (Part C).
**Scope:** the 25 documents in `tests/test_corpus/` (main corpus) and the held-out set in `tests/test_corpus/held_out/` (Story 10.1, Task 4).
**Entity types:** `PERSON`, `LOCATION`, `ORG` (schema in `README.md`).

## How to read this document

- Every rule has a stable ID (`G…` general, `P…` PERSON, `O…` ORG, `L…` LOCATION). Each annotation edit cites one ID in the change log. The JSON stays as it is: citations are kept out of the annotation files.
- **Part A** lists rules settled by Epic 10 or Story 10.1, plus G7 (nesting), which Lionel added at approval. **Part B** holds the rules decided at STOP A from the open questions. They keep their IDs `Q1`–`Q18`, so a change-log row cites e.g. `Q14`. **Part C** holds the amendments decided on 2026-10-03 (`A1`–`A7`). They are cited the same way.
- Examples are quoted from the corpus as `document: "text"`. **+** marks a correct annotation, **−** marks the current annotation that the rule corrects.
- After approval, a rule changes only through the Amendments table (end of file). A case no approved rule covers goes back to Lionel first. It is not annotated in the meantime (AC2).

---

## Part A: Settled rules

### General

**G1. Three types only.** Annotate only PERSON, LOCATION and ORG. Email addresses, phone numbers, dates, amounts, reference codes and job titles are not annotated.
- `email_chain`: "Mobile: +33 6 12 34 56 78" → nothing.

**G2. The span is the name, whole, and nothing else.** No leading or trailing whitespace or punctuation, and no surrounding words (verbs, prepositions, conjunctions, descriptions). The name is not cut short either. [Story 10.1, 1.4]
- − `email_chain`: ORG `"Microsoft "` (trailing space; 13 such spans in the corpus) → + `"Microsoft"`.
- − `interview_09`: ORG "Menée par KPMG France" → + ORG "KPMG France".
- − `meeting_minutes`: ORG "Partner chez Deloitte France" → + ORG "Deloitte France".
- − `email_chain`: PERSON "Nadia" in "Mme Nadia Amrani?" → + "Nadia Amrani".

**G3. Offsets.** `start_pos`/`end_pos` index the text as read by `Path.read_text(encoding="utf-8")` (LF line endings); `end_pos` is exclusive; `text[start_pos:end_pos] == entity_text` holds for every entry. [Story 10.1, 1.4, 3.5]

**G4. One annotation per occurrence, every occurrence.** Each mention of an entity gets exactly one annotation. Two annotations never share the same text, type and offsets. A string annotated in one place is annotated at every occurrence of the same entity, unless a rule says otherwise. [Story 10.1, 1.4, 3.4(ii)]
- − `interview_01`: "TechCorp" (ORG, 641–649) annotated twice → one.
- − "CNIL" appears in 7 documents (e.g. `interview_08`: "Nous conseillons la CNIL") with 0 annotations → one ORG per occurrence.

**G5. No same-type overlaps.** Two annotations of the same type never overlap. Annotations of different types may overlap only as G7 allows. [Story 10.1, 1.4; G7 added at approval]
- − `interview_09`: PERSON "Anne Marion Chauveau" and PERSON "Marion Chauveau" over the same words → one span (which one: Q9).

**G6. Annotate the text, not a tool's output.** Each annotation follows from a rule applied to the text. A detector hit can point at a candidate on the main corpus, but it never justifies an annotation by itself. Held-out annotations are made by hand, never pre-annotated by the detector or `auto_annotate_corpus.py`. [Story 10.1, AC5, Judgment Calls]

**G7. Nesting: a place inside an ORG name gets a nested LOCATION only if it says where the organisation is.** Ask: *does this place tell me where this organisation, or this branch of it, is?* If it does, the whole name is ORG and the place also gets its own LOCATION inside it. If the place word is just part of a brand name, nothing is nested. Nesting is limited to places: an ORG never contains a nested PERSON (A1), and a PERSON never contains a nested LOCATION. This is the only cross-type overlap allowed. [Lionel, STOP A 2026-10-02 (one rule for Q3 and Q5); meaning test added by amendment A2, 2026-10-03]
- + `interview_01`: "Microsoft France" → ORG "Microsoft France" + LOCATION "France" (the French branch).
- + `interview_13`: "INSA Lyon" → ORG "INSA Lyon" + LOCATION "Lyon".
- + `interview_04`: "CHU de Lille" → ORG "CHU de Lille" + LOCATION "Lille". `interview_06`: "Banque de France" → ORG + LOCATION "France".
- + `interview_03`: "Préfecture de la Gironde" → ORG + LOCATION "Gironde" (preposition and article outside the LOCATION, L2).
- + `interview_09`: "Banque Régionale du Sud" → ORG + LOCATION "Sud" (the bank of the South: it says where the bank is, A3).
- − `interview_15`: "Palo Alto Networks" → ORG only. The place word is part of the brand.
- − `interview_03`: "Orange Business Services", `interview_11`: "Orange Cyberdefense" → ORG only. Here "Orange" is a company name, not the city (Lionel).
- − `interview_01`: "Université Claude Bernard", `board_minutes`: "CMS Francis Lefebvre" → ORG only, no nested PERSON (A1).
- A place used outside any ORG name is a plain LOCATION (L1).

### PERSON

**P1. PERSON = a named human individual.** Real public figures and invented people count alike. A capitalised phrase that is not the name of a person is not PERSON: subject lines, section headings, place names, company names, team names, job titles. [Story 10.1, F4 junk list in 3.3]
- + `board_minutes`: "M. Yann LeCun" → "Yann LeCun".
- − `email_chain`: "Lancement Projet" (5), "Validation Architecture" (5): subject-line words → removed.
- − `partnership_agreement`, `sales_proposal`: "Société Générale" (4) and "Crédit Agricole" (3) as PERSON → ORG (O1).
- − `meeting_minutes`: "Tour Montparnasse" as PERSON; `interview_12`: "Hôtel Plaza" as PERSON → not PERSON (Q16).
- − `interview_03`: "On échange", `interview_04`: "Une équipe" → removed.

**P2. Titles are excluded from the span.** Excluded: M., MM., Mme, Mmes, Mlle, Monsieur, Madame, Dr, Dr., Docteur, Pr, Pr., Professeur, Me, Maître. A title whose gender does not match the name does not change the span. [AC1; README "Annotation Policy: Titles", Story 5.3. "MM.", "Mlle" and "Docteur" are added to the README list; "MM." and "Docteur" occur in the corpus, and the AC1 list ends with "…"]
- + `interview_01`: "Dr. Marie Dubois" → "Marie Dubois".
- + `hr_announcement`: "MM. Alexandre Jin, Romain Duval et Mmes Laura Martin, Nadia Amrani" → four PERSON spans without titles.
- + `interview_07`: "Mme Hervé Morin" → "Hervé Morin".
- − `interview_01`: "Docteur Dubois", `interview_08`: "Docteur Cohen" → "Dubois", "Cohen".
- − `partnership_agreement`: "Contact Mme" (4), `incident_report`: "Email Mme" → removed (no name inside).

**P3. Hyphenated given names and hyphenated surnames are annotated whole.** [AC1]
- + `board_minutes`: "M. Jean-Luc Moreau" → "Jean-Luc Moreau". − 16 annotations read "Luc Moreau" (e.g. `audit_summary`, `contract_memo`).
- + `interview_04`: "Mme Anne-Sophie Jannot" → "Anne-Sophie Jannot". − "Anne-".
- + `interview_13`: "Mme Gwenaëlle Avice-Huet". − `partnership_agreement`: "Gwenaëlle Avice-".
- + `interview_13`: "Nathalie Perrin-Gilbert", `interview_15`: "Édouard Fernandez-Bollo". − "Nathalie Perrin-", "Édouard Fernandez-".

**P4. Particle surnames are annotated whole** (le, la, de, du, des, d', van, van der, von, Van Den, …). [AC1; epic 10.3 AC4]
- + `board_minutes`: "M. Jean-Charles Le Goff" → "Jean-Charles Le Goff". − 6 annotations read "Charles Le" (`audit_summary`, `incident_report`, `interview_07`).
- + `interview_04`: "Mme Sylvie van der Werf" → "Sylvie van der Werf". − "Sylvie van".
- + `interview_04`: "M. Jean-Baptiste Chasseloup de Laubat" → "Jean-Baptiste Chasseloup de Laubat". − "Baptiste Chasseloup".
- + `interview_11`: "M. Michel Van Den Berghe" → one span. − "Michel Van" + "Den Berghe".
- + `interview_07`: "M. Yves Le Gélard", `interview_13`: "M. Yves Le Breton". − "Yves Le" (2).
- + `interview_09`: "Mme Isabelle de Silva", "M. Alexandre de Rothschild"; `board_minutes`: "M. Yann du Rusquec".
- **Negative: de/du/de la + ORG is not a particle.** The person ends before "de"; the ORG is annotated under O1. [Story 10.1, 1.3]
  - `interview_08`: "Professeur Raja Chatila de Sorbonne Université" → PERSON "Raja Chatila", ORG "Sorbonne Université".
  - `interview_13`: "Mme Audrey Lebel de la French Tech Lyon" → PERSON "Audrey Lebel" (the rest: Q3).
  - `interview_14`: "Mme Régine Ballonad de Printemps" → PERSON "Régine Ballonad", ORG "Printemps".
  - `interview_11`: "Mme Natacha Reynaud de Thales" → PERSON "Natacha Reynaud", ORG "Thales".
  - `interview_08`: "Mme Laurence Devillers du CNRS" → PERSON "Laurence Devillers", ORG "CNRS".
  - `email_chain`: "Mme Émilie Rousseau de Wavestone" → PERSON "Émilie Rousseau", ORG "Wavestone".
  - `interview_02`: "Mme Isabelle Moreau de la DRH" → PERSON "Isabelle Moreau" ("DRH": O3).
  - de + place: Q12.

**P5. Mc/Mac names are annotated whole.** [Epic 10.3 AC5; held-out hard case, AC5]
- + `contract_memo`, `partnership_agreement`: "Mme Sarah McDonald" → "Sarah McDonald". − "Mc" (2) → removed.

**P6. Job titles and roles are not PERSON and are not part of a PERSON span.** [AC1]
- − "Directeur Commercial" (9: `email_chain`, `hr_announcement`, …), "Architecte Cloud" (6), "Lead Developer" (3), "General Counsel" (4), "Account Manager" (2) → removed.
- − `sales_proposal`: "Valérie Blanc DRH" → "Valérie Blanc".
- − `audit_summary`, `incident_report`: "Rousseau, Responsable" (3) → the comma pulled in the next role word. The person is already annotated as "Catherine Rousseau"; the artefact is removed.

### ORG

**O1. ORG = a named organisation.** Companies, public bodies and regulators (CNIL, ANSSI, ACPR, ANSM), firms (Deloitte, KPMG, Bredin Prat), schools and universities, banks, research institutes, associations and unions, media, international bodies. [AC1]
- + `interview_11`: "On a été audité par la CNIL" → "CNIL". `interview_03`: "L'ANSSI nous a envoyé" → "ANSSI". (0 annotations of either at draft time.)
- + `hr_announcement`: "(Deloitte, M. Jean-Luc Moreau)" → "Deloitte".
- + `interview_01`: "École Polytechnique", "Université Claude Bernard"; `interview_06`: "BNP Paribas", "Crédit Agricole", "Banque de France".
- + `interview_15`: "SEKOIA.IO"; `interview_12`: "Simplon.co" (the domain-like ending is part of the name).
- − `interview_06`: PERSON "Paribas, Crédit" → ORG "BNP Paribas" + ORG "Crédit Agricole".

**O2. Job titles are not ORG**, including VP + region forms. [AC1]
- − `partnership_agreement`: ORG "VP Europe" (7), "VP Finance Europe"; `contract_memo`: ORG "VP Sales Europe" → removed.

**O3. Roles and role acronyms are not ORG** (CEO, CTO, CFO, CDO, CSO, DPO, RSSI, DSI, DRH, COMEX, "VP Engineering", "VP Sales", …). [AC1]
- `interview_06`: "Mon CTO est M. Romain Niccoli" → no ORG. `interview_15`: "Notre COMEX s'est réuni" → no ORG. `hr_announcement`: "VP Engineering" → no ORG.

**O4. A company name is never LOCATION**, even when it contains a place name. [AC1, LOCATION bullet]
- `interview_15`: "Palo Alto Networks" → ORG. The city in `contract_memo`: "GlobalTech Industries (Palo Alto, Californie)" → LOCATION "Palo Alto". − Today "Palo Alto" is PERSON (9) in both uses.

### LOCATION

**L1. LOCATION = a named geographic place, French or foreign.** [AC1]
- + `interview_01`: "Londres et Berlin"; `interview_02`: "Wolfsburg", "Stuttgart et Turin"; `interview_04`: "Genève", "Atlanta", "Amsterdam". None of the last six is annotated at draft time.
- + `interview_05`: "Cabinet Mercier & Associés, Nice" → LOCATION "Nice". − PERSON "Associés, Nice".

**L2. Prepositions are excluded from the span** (à, au, aux, en, de, d', du, des). [AC1; same list as the app's `strip_french_prepositions`]
- `interview_01`: "nos bureaux à Toulouse et Marseille" → "Toulouse", "Marseille". `interview_15`: "en remote depuis les US" → the preposition is excluded (whether "US" is LOCATION: Q14).
- For an article that belongs to the place name ("la Défense", "du Havre"), see Q15.

**L3. One span per place.** A list of places gets one annotation per place name. [Follows from G2/G4]
- − `interview_03`: PERSON "Mérignac, Pessac" → LOCATION "Mérignac", "Pessac", and "Talence".

---

## Part B: Rules decided at STOP A (Q1–Q18)

Each item keeps its question, examples, the decided rule and the reason for it. "Approved default" means Lionel accepted the proposal unchanged. **CHANGED** means his answer replaced the proposal; the original proposal is kept in the decision record at the end of this file.

**Q1. Salutation lines.** `email_chain`: "Laurent, Marie," (email 3) is a greeting to two people (Laurent Benoit, Marie Dubois). The same thread has a bare "Marie," on a greeting line (email 2), "Marie, pour la réunion du 12" (email 3), the signature "Laurent" (email 2) and "Bonne initiative Laurent." (email 3).
- **Rule (approved default):** "Laurent, Marie," → two PERSON, "Laurent" and "Marie". Each bare first name used to address or sign is a PERSON ("Marie", "Laurent").
- Why: each is one person; consistent with epic F8 and 10.4 AC1. Today one PERSON "Laurent, Marie" covers both, and the bare forms are missing.

**Q2. "Last, First".** The corpus has one genuine inverted name: `interview_02`: "Participant: Dubois, Jean-Marc (Chef d'équipe production)". Today it is annotated "Dubois, Jean-". Of the 37 comma annotations, this is the only genuine "Last, First": "Laurent, Marie" is a salutation (Q1), and the other 35 are artefacts (P6, O1).
- **Rule (approved default):** one PERSON span "Dubois, Jean-Marc", comma included.
- Why: one person, one span, consistent with P3 (whole name). The alternative is two spans, "Dubois" and "Jean-Marc".

**Q3. Organisation + country, region or city.** `interview_01`, `email_chain`, `meeting_minutes`, `project_report`: "Microsoft France"; also "KPMG France", "Deloitte France", "Google Cloud France", "IBM Europe", "Pfizer Europe", "AstraZeneca UK", "TechSolutions UK", "McKinsey Paris", "BETC Paris", "INSA Lyon", "Keolis Lyon", "French Tech Lyon", "INRIA Saclay".
- **Rule (CHANGED by Lionel):** one ORG covering the name and its geographic qualifier, **plus a nested LOCATION** for the place (G7): "Microsoft France" = ORG "Microsoft France" + LOCATION "France"; "INSA Lyon" = ORG + LOCATION "Lyon"; "DataCorp Europe" = ORG + LOCATION "Europe".
- Why: the ORG stays whole (epic F9, 10.4 AC4), and the place is still a place a reviewer must see.

**Q4. Legal forms and descriptor words in ORG spans.** `board_minutes`: "TechSolutions France SAS", "CloudTech SAS"; `partnership_agreement`: "GlobalTech Industries Inc."; `interview_02`: "AutoMotive SA"; `interview_09`: "Rothschild & Co". Descriptors: `interview_15`: "cabinet CMS Francis Lefebvre", `partnership_agreement`: "Cabinet Bredin Prat", `meeting_minutes`: "Fond Ardian", `interview_07`: "Groupe Industriel Normandie", `interview_05`: "Cabinet Mercier & Associés".
- **Rule (approved default):** a legal form attached to the name (SAS, SA, Inc., & Co, & Associés) is inside the span. A leading descriptor (cabinet, société, groupe, fonds, agence, startup, coopérative) is outside the span when the rest is a name by itself ("CMS Francis Lefebvre", "Bredin Prat", "Ardian", "Mercier & Associés"). It is inside when the rest would not be a name ("Groupe Industriel Normandie", "Banque Régionale du Sud"). A place inside the name is nested under G7 ("Normandie").
- Why: the span is the name as the organisation writes it. − Today: "TechSolutions France SA" (the "S" of SAS cut off), PERSON "Cabinet Mercier", "Cabinet Bredin", "Fond Ardian", and ORG "Le Group" + PERSON "Industriel Normandie".

**Q5. Organisations whose name contains a place.** `interview_03`: "Mairie de Bordeaux", "Préfecture de la Gironde", "Région Nouvelle-Aquitaine"; `interview_04`: "CHU de Lille", "Université de Lille"; `interview_02`: "Université de Strasbourg"; `interview_13`: "Métropole de Lyon"; `interview_05`: "Tribunal de Commerce de Paris", "Cour d'Appel de Paris"; `interview_10`: "Chambre d'Agriculture d'Eure-et-Loir"; `interview_07`: "La Région Normandie, représentée par M. Hervé Morin".
- **Rule (CHANGED by Lionel):** the whole name is one ORG, **plus a nested LOCATION** for the place inside it (G7): "CHU de Lille" = ORG + LOCATION "Lille"; "Région Normandie" = ORG + LOCATION "Normandie". A place used as a place, outside an ORG name, is a plain LOCATION ("la région Occitanie" in `interview_11`; Q12).
- Why: Lionel chose one rule for Q3 and Q5. The schema allows overlapping spans, and the scorer matches each annotation on its own text and type, so nesting costs nothing in the scorer.

**Q6. Products, services, platforms, events, projects.** `email_chain`: "Azure Cloud Platform (région France Central)", "Azure AD"; `project_report`: "Licences Microsoft Azure"; `audit_summary`: "Microsoft Azure (M. Romain Niccoli): ✓ Conforme", "Palo Alto Cortex XSOAR", "Azure Backup"; `incident_report`: "Azure West Europe", "Microsoft DART: M. John Lambert"; `partnership_agreement`: "IBM Watson, Google AI", "VivaTech", "Microsoft Ignite"; `meeting_minutes`: "SAP S/4HANA"; `interview_14`: "Salesforce Commerce Cloud"; `email_chain`: "Projet Phoenix".
- **Rule (approved default):**
  (a) a company name used alone is ORG, even when it stands for its product ("Salesforce déployé", "on utilise Splunk");
  (b) a product, service, cloud region, event, project or certification name is not annotated ("Azure", "Azure AD", "Cortex XSOAR", "France Central", "VivaTech", "Phoenix", "ISO 27001", "SecNumCloud");
  (c) vendor + product ("Microsoft Azure", "Google Cloud", "IBM Watson", "Microsoft DART") is one ORG when it designates the supplier organisation (it has contacts, signs, audits, is a subcontractor). Otherwise only the vendor name is ORG, under (a).
- Why: what gets pseudonymised is who acts, not the tools used. This keeps vendor recall. − Today: PERSON "Azure Cloud", "Azure West", "Azure Backup", "Azure Patch"; ORG "IBM Watson", "Google AI".

**Q7. Internal departments, teams and committees.** `contract_memo`: "Direction Juridique", "Direction des Achats"; `hr_announcement`: "Équipe Security", "Équipe Engineering"; `meeting_minutes`: "Comité de Direction"; `board_minutes`: "Conseil d'administration"; `incident_report`: "cellule de crise", "SOC".
- **Rule (approved default):** not ORG.
- Why: this extends AC1 (COMEX and DRH are not ORG). These name a part of an organisation, not one a reader can identify. − Today: PERSON "Direction Juridique", "Équipe Security", "Ressources Humaines".

**Q8. Partial names.** Surname only: `board_minutes`: "Mme Moreau", "M. Arnaud"; speaker labels `interview_01`: "Dr. Dubois:"; `interview_06`: "Rodriguez:". First name only: `hr_announcement`: "Kevin rejoint le COMEX", "Julie pilotera". Short company forms: `interview_15`: "SecurePay"; `interview_05`: "SoftTech", "DataCorp".
- **Rule (approved default):** each one is annotated with its type (PERSON or ORG), at every occurrence.
- Why: each identifies the entity, so a pseudonymised document must replace it. Matches current practice (PERSON "Moreau" 15, "Dubois" 8).

**Q9. Several given names.** `interview_09`: "Mme Anne Marion Chauveau"; `interview_12`: "Mme Marcy Ericka Charollois". Both are annotated twice today (G5).
- **Rule (approved default):** one PERSON covering every given name and the surname as written ("Anne Marion Chauveau", "Marcy Ericka Charollois").
- Why: whole-name principle (P3). The alternative is to treat the first word as a separate first name.

**Q10. Initials.** `interview_02`: "J-M. Dubois" (3 occurrences, none annotated today).
- **Rule (approved default):** one PERSON "J-M. Dubois", including the initials and their dot.
- Why: the initials are part of how the person is named here, as with P3. Without them the span is a surname only (Q8).

**Q11. Apostrophes and inner capitals.** `interview_10`: "M. Sébastien Floc'h" (today "Sébastien Floc"); `partnership_agreement`: "M. Brian O'Connor"; `hr_announcement`, `interview_08`: "M. Yann LeCun" (today "Yann Le" twice, whole in `board_minutes`).
- **Rule (approved default):** whole name, apostrophe and inner capital included.
- Why: same principle as P3–P5.

**Q12. "de" + place after a name.** `interview_05`: "Me Isabella Ferrari de Milan" (today one PERSON); `interview_11`: "Mme Nacira Salvan de la région Occitanie" (today PERSON "Nacira Salvan de la").
- **Rule (approved default):** "de" followed by a place is not a particle: PERSON "Isabella Ferrari" + LOCATION "Milan"; PERSON "Nacira Salvan" + LOCATION "Occitanie". Contrast P4: "Chasseloup de Laubat" (no place or ORG follows), where the particle stays in the name.
- Why: it marks origin or affiliation, like the de + ORG negative in P4.

**Q13. Stage names and pseudonyms of real people.** `interview_14`: "Léna Situations", "Enjoy Phoenix (Marie Lopez)".
- **Rule (approved default):** PERSON.
- Why: they identify an individual as surely as a legal name.

**Q14. "US", "USA", "UK" and country abbreviations.** `partnership_agreement`: "Palo Alto, CA 94303, USA", "M. Brian O'Connor (US)"; `interview_15`: "depuis les US"; `audit_summary`: "sous-traitants US"; `board_minutes`: "Expansion internationale: UK, Allemagne, Benelux" (today LOCATION "UK"); `interview_06`: "directeur UK"; `audit_summary`: "Transferts hors UE".
- **Rule (CHANGED by Lionel):** "US", "USA", "UK" and "UE" are **always LOCATION, at every occurrence**, including adjectival use ("sous-traitants US", "directeur UK"). Inside an ORG name they are a nested LOCATION (G7: "TechSolutions UK", "AstraZeneca UK").
- Why: a single string-level rule, with no noun/adjective judgment.

**Q15. Article that is part of a place name.** `interview_01`: "notre bureau à la Défense" (today LOCATION "Défense"); `interview_07`: "notre usine du Havre".
- **Rule (approved default):** keep the article when it is written separately: "la Défense". When the article is fused with a preposition ("du Havre", "au Havre"), the span is "Havre".
- Why: the app's preposition pattern deliberately keeps la/le/les as part of names ("La Rochelle", "Le Mans": comment in `french_patterns.py`), and a fused article cannot be split off inside a span.

**Q16. Buildings, sites, venues and street addresses.** `meeting_minutes`: "Salle de réunion A, Tour Montparnasse, Paris"; `interview_06`: "Station F"; `interview_12`: "manager à l'Hôtel Plaza Athénée"; `board_minutes`, `email_chain`, `partnership_agreement`, `sales_proposal`: "45 Avenue de la Grande Armée, 75016 Paris", and `contract_memo`: "45 Avenue de la Grande Armée, Paris 16ème" (today PERSON "Grande Armée", 4); `sales_proposal`: "123 Avenue de la République, 13001 Marseille"; `partnership_agreement`: "2500 Innovation Drive, Palo Alto, CA 94303, USA"; `interview_14`: "L'entrepôt de Lesquin".
- **Rule (approved default):** a named building or venue is LOCATION ("Tour Montparnasse", "Station F"). A hotel or shop named as an employer or business is ORG ("Hôtel Plaza Athénée"). In a street address, the street name is LOCATION ("Avenue de la Grande Armée") and the city is a separate LOCATION ("Paris"). House numbers, postcodes, state codes ("CA") and generic rooms ("Salle de réunion A") are not annotated. "USA" at the end of an address is LOCATION (Q14).
- Why: an address identifies people and premises, and the reviewer should be offered it. Number and postcode spans have no entity type here (G1).

**Q17. Place granularity.** `board_minutes`: "Benelux"; `partnership_agreement`: "partenariat stratégique en Europe"; `interview_10`: "Mme Sophie Rousseau en Eure", "M. Jean Dupont en Île-de-France"; `interview_05`: "Sophia-Antipolis" (not annotated today; its second half sits inside the junk ORG "Antipolis et DataCorp Europe").
- **Rule (approved default):** every named place is LOCATION at any level: supranational (Europe, Benelux), country, region, département, city, district. A place inside an ORG name is a nested LOCATION under G7 (`interview_04`: "ARS Hauts-de-France" → ORG + LOCATION "Hauts-de-France"; `interview_10`: "Ferme de Beauce" → ORG + LOCATION "Beauce").
- Why: any place can narrow down who a person is. The scorer ignores granularity anyway (exact text match).

**Q18. Defined-term aliases and abbreviations of organisations.** `partnership_agreement`: 'Ci-après dénommée "TECHSOLUTIONS"' and "GLOBALTECH", used 44 and 42 times; `sales_proposal`: "Participants BRS" (Banque Régionale du Sud) and the reference "PROP-2024-BRS-001".
- **Rule (approved default):** an alias or abbreviation that refers to the organisation is ORG at every occurrence ("TECHSOLUTIONS", "GLOBALTECH", "BRS"). An abbreviation inside a reference code is not annotated (G1).
- Why: the alias names the company, so leaving it would undo the pseudonymisation of the full name. **Impact:** about 86 new ORG annotations in `partnership_agreement` alone, against 131 ORG today. This is the largest single effect on ORG counts in the repair.

---

## Decision record (STOP A)

Approved by Lionel on 2026-10-02. Reviewed draft: commit `e7835a3`, sha256 `57ceba37a60014c900637c441c95db3b4fc8e3c059821486698b604d101fe37e`.

| Item | Decision |
|------|----------|
| Part A (G1–G6, P1–P6, O1–O4, L1–L3) | Approved as drafted |
| G7 | Added by Lionel (one nesting rule for Q3 and Q5; cross-type overlap allowed, same-type still forbidden) |
| Q1, Q2, Q4, Q6–Q13, Q15–Q18 | Proposed default approved |
| Q3 | **Changed.** Proposed: one ORG, no LOCATION inside. Decided: ORG + nested LOCATION |
| Q5 | **Changed.** Proposed: one ORG, no nesting of any type. Decided: ORG + nested LOCATION |
| Q14 | **Changed.** Proposed: LOCATION as a noun, nothing as an adjective. Decided: always LOCATION, every occurrence |

## Part C: Amendments decided on 2026-10-03

These came up during the repair. Lionel decided them on 2026-10-03. Cite them by ID.

**A1. A person's name inside an ORG name.** ORG only, no nested PERSON. G7 nesting is limited to places.
- `interview_01`: "Université Claude Bernard"; `interview_05`: "Mercier & Associés"; `board_minutes`: "CMS Francis Lefebvre", "Bredin Prat", "August Debouzy"; `meeting_minutes`: "Michael Page" → ORG only.

**A2. Place words in ORG names are judged by meaning (G7 test).** Nest a LOCATION only when the place says where the organisation or branch is ("Microsoft France", "INSA Lyon", "CHU de Lille"). A place word that is part of a brand name gets nothing ("Palo Alto Networks", "Orange Business Services", "Orange Cyberdefense").

**A3. Compass-point regions.** A capitalised "le Nord" / "le Sud" used as a region is LOCATION. The span is the name without the article ("Nord", "Sud"): the article is not part of the name, as with "la France", unlike "la Défense" (Q15). Inside an ORG name it follows G7 ("Sud" in "Banque Régionale du Sud" is nested: it says where the bank is). Lowercase directions ("au nord de") are not annotated.
- `interview_14`: "Mme Carole Petit pour le Nord", "Mme Nadia Kadem pour le Sud" → LOCATION "Nord", "Sud".

**A4. "l'État" as an actor** is not annotated. Named state bodies stay ORG (O1).
- `interview_13`: "L'État soutient via l'ANCT" → nothing for "État"; ORG "ANCT".

**A5. "EU"** is treated like "UE" (Q14): always LOCATION, at every occurrence.
- `partnership_agreement`: "Autres pays EU", "Mme Emer Cooke (EU)" → LOCATION "EU".

**A6. Arrondissements are their own LOCATION.** "Paris 16ème" = LOCATION "Paris" + LOCATION "16ème". A bare "du 7ème" = LOCATION "7ème", with the preposition excluded (L2). Postcodes stay unannotated (Q16).
- `contract_memo`: "Paris 16ème"; `interview_13`: "M. Jean-Yves Sécheresse du 7ème".

**A7. A place inside a job title or team name is LOCATION** (L1). The job title or team itself is still not annotated (O2, P6, Q7). This was confirmed by Lionel on 2026-10-03; it had been applied at the repair as an interpretation.
- `partnership_agreement`: "VP Europe" (7), "Regional Manager France", "Équipe Europe"; `contract_memo`: "VP Sales Europe"; `interview_12`: "Leur directeur France" → LOCATION on the place word.

## Amendments

Changes after approval (AC2). Each row is also recorded in the story's Dev Notes "Guidelines Approval Record".

| Date | Rule ID | Change | Approved by |
|------|---------|--------|-------------|
| 2026-10-03 | A1 | A person's name inside an ORG name: ORG only, no nested PERSON | Lionel |
| 2026-10-03 | A2, G7 | G7 rewritten to a meaning test: nest a place only if it says where the organisation or branch is; brand-name place words get nothing | Lionel |
| 2026-10-03 | A3 | Capitalised "le Nord" / "le Sud" as a region is LOCATION; inside an ORG it follows G7; lowercase directions are not annotated | Lionel |
| 2026-10-03 | A4 | "l'État" as an actor is not annotated | Lionel |
| 2026-10-03 | A5 | "EU" is always LOCATION, like "UE" | Lionel |
| 2026-10-03 | A6 | An arrondissement is its own LOCATION ("16ème", "7ème"). This changed the proposed default, which was to leave it unannotated | Lionel |
| 2026-10-03 | A7 | A place inside a job title or team name is LOCATION (interpretation confirmed) | Lionel |

## Pending amendments

_None open._
