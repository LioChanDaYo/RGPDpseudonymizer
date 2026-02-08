# Performance Test Documents

Test documents for Story 4.5 performance benchmarks. Each document is realistic
French text (interview transcripts, business documents) following the style
patterns of the existing test corpus at `tests/test_corpus/`.

## Document Summary

| File | ~Words | Style | PERSON | LOCATION | ORG | Entity Density |
|------|--------|-------|--------|----------|-----|----------------|
| `sample_2000_words.txt` | 2061 | Interview transcript | ~8 | ~2 | ~1 | Low |
| `sample_3500_words.txt` | 3426 | Board meeting minutes | ~20 | ~5 | ~3 | Medium |
| `sample_5000_words.txt` | 5067 | Annual report | ~35 | ~8 | ~5 | High |

## Entity Details

### sample_2000_words.txt (Low Density)

**PERSON (~8):** Philippe Garnier, Hélène Bernard, Laurent Dupont, Claire Renaud,
Antoine Moreau, Isabelle Petit

**LOCATION (~2):** Nantes

**ORG (~1):** Centre de Recherche Industrielle (in header only)

### sample_3500_words.txt (Medium Density)

**PERSON (~20):** Jean-Marc Lefort, Nathalie Rousseau, Patrick Dufour,
Véronique Blanc, Christophe Lemaire, Sandrine Morel, Thierry Faure,
Élise Gauthier, Olivier Marchand, Bruno Lefèvre, Frédéric Bonnet,
Caroline Vincent, Yannick Pelletier, Amina Khelifi, Jacques Attali,
Marc Girard, Sylvie Prost, Arnaud Leblanc, Béatrice Fournier

**LOCATION (~5):** Lyon, Toulouse, Strasbourg, Marseille, Nice, Lille,
Munich, Milan, Barcelone, Bordeaux, Sophia Antipolis, Montpellier,
Hanovre, Grenoble, Genève

**ORG (~3):** Ernst & Young, McKinsey, KPMG, Nexus Technologies,
Amaris Group, École Centrale de Lyon, INSA

### sample_5000_words.txt (High Density)

**PERSON (~35):** Henri Beaumont, Sophie Delacroix, Françoise Lambert,
Nicolas Perrin, Catherine Dubois, Stéphane Roche, Bernard Arnault,
Thomas Fischer, Maria Garcia, Giovanni Rossi, Ingrid Johansson,
Pierre Dupont, Audrey Lefebvre, Karim Benali, Pascal Lefranc,
Anne-Sophie Martin, Julien Mercier, Rémi Chartier, Amina Khelifi,
Alexandre Nguyen, François Moreau, Lucie Renard, Élise Gauthier,
Véronique Blanc, Yannick Pelletier, Rachida Benmoussa,
Claire Martin-Dupuis, Philippe Dauman, Marc Girard, Christine Pasquier,
David Leroy, Raphaël Vidal, Samira Hamadi, and more

**LOCATION (~8):** Lyon, Toulouse, Grenoble, Paris, Nantes, Rennes,
Francfort, Munich, Stuttgart, Düsseldorf, Madrid, Valence, Séville,
Milan, Turin, Bologne, Stockholm, Göteborg, Helsinki, Lisbonne, Zurich,
Vienne

**ORG (~5):** CNRS, Roland Berger, Tecnosur, Bureau Veritas,
École polytechnique fédérale, École normale supérieure de Lyon,
Musée des Confluences, Cité des Sciences

## Usage

These documents are used by `tests/performance/` benchmark tests:
- `test_single_document_benchmark.py` — NFR1 validation (<30s per document)
- `test_batch_performance.py` — NFR2 batch processing reference
- `test_stress.py` — Stress testing with large documents
