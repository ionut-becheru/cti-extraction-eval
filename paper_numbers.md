# Paper numbers

Every number recommended for the paper, with the script and run that produced it. Regenerate with `scripts/aggregate_tables.py` then `scripts/write_paper_numbers.py`.

| key | value | run | script |
|---|---|---|---|
| T1.gazetteer_microF1.aptner | {"value": 0.2429, "ci95": [0.2118, 0.2783]} | N0_dictionary_ner | scripts/gold_ner/eval_dictionary_ner.py |
| T1.gazetteer_microF1.dnrti | {"value": 0.2497, "ci95": [0.2161, 0.2794]} | N0_dictionary_ner | scripts/gold_ner/eval_dictionary_ner.py |
| T1.gazetteer_microF1.cyner | {"value": 0.1487, "ci95": [0.0955, 0.1997]} | N0_dictionary_ner | scripts/gold_ner/eval_dictionary_ner.py |
| T1.gazetteer_microF1.annoctr | {"value": 0.3031, "ci95": [0.2739, 0.3343]} | N0_dictionary_ner | scripts/gold_ner/eval_dictionary_ner.py |
| T1.gazetteer_microF1.attacker | {"value": 0.117, "ci95": [0.0321, 0.2153]} | N0_dictionary_ner | scripts/gold_ner/eval_dictionary_ner.py |
| T2.Regex+gazetteer (thesis).aptner | {"strict_F1": 0.2429, "relaxed_F1": 0.2429, "ci95_strict": [0.2118, 0.2783]} | N0_dictionary_ner | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Regex+gazetteer (thesis).dnrti | {"strict_F1": 0.2497, "relaxed_F1": 0.2689, "ci95_strict": [0.2161, 0.2794]} | N0_dictionary_ner | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Regex+gazetteer (thesis).cyner | {"strict_F1": 0.1487, "relaxed_F1": 0.2089, "ci95_strict": [0.0955, 0.1997]} | N0_dictionary_ner | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Regex+gazetteer (thesis).annoctr | {"strict_F1": 0.3031, "relaxed_F1": 0.3243, "ci95_strict": [0.2739, 0.3343]} | N0_dictionary_ner | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Regex+gazetteer (thesis).attacker | {"strict_F1": 0.117, "relaxed_F1": 0.1809, "ci95_strict": [0.0321, 0.2153]} | N0_dictionary_ner | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.RoBERTa-base (ft).aptner | {"strict_F1": 0.6509, "relaxed_F1": 0.7067, "ci95_strict": [0.6298, 0.6733]} | E2_ft/roberta_*_coarse_s13 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.RoBERTa-base (ft).dnrti | {"strict_F1": 0.8406, "relaxed_F1": 0.88, "ci95_strict": [0.8193, 0.8615]} | E2_ft/roberta_*_coarse_s13 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.RoBERTa-base (ft).cyner | {"strict_F1": 0.8171, "relaxed_F1": 0.8937, "ci95_strict": [0.7853, 0.8492]} | E2_ft/roberta_*_coarse_s13 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.RoBERTa-base (ft).annoctr | {"strict_F1": 0.6758, "relaxed_F1": 0.718, "ci95_strict": [0.6433, 0.707]} | E2_ft/roberta_*_coarse_s13 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.RoBERTa-base (ft).attacker | {"strict_F1": 0.642, "relaxed_F1": 0.7469, "ci95_strict": [0.5587, 0.7225]} | E2_ft/roberta_*_coarse_s13 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.DeBERTa-v3-base (ft).aptner | {"strict_F1": 0.6668, "relaxed_F1": 0.7276, "ci95_strict": [0.6454, 0.6909]} | E2_ft/deberta-v3_*_coarse_s13 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.DeBERTa-v3-base (ft).dnrti | {"strict_F1": 0.8386, "relaxed_F1": 0.8728, "ci95_strict": [0.8158, 0.8602]} | E2_ft/deberta-v3_*_coarse_s13 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.DeBERTa-v3-base (ft).cyner | {"strict_F1": 0.8528, "relaxed_F1": 0.9084, "ci95_strict": [0.8235, 0.8814]} | E2_ft/deberta-v3_*_coarse_s13 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.DeBERTa-v3-base (ft).annoctr | {"strict_F1": 0.7012, "relaxed_F1": 0.745, "ci95_strict": [0.6709, 0.7342]} | E2_ft/deberta-v3_*_coarse_s13 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.DeBERTa-v3-base (ft).attacker | {"strict_F1": 0.6361, "relaxed_F1": 0.7148, "ci95_strict": [0.5544, 0.7059]} | E2_ft/deberta-v3_*_coarse_s13 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.SecureBERT~2.0-base (ft).aptner | {"strict_F1": 0.6313, "relaxed_F1": 0.698, "ci95_strict": [0.6087, 0.6556]} | E2_ft/securebert20_*_coarse_s13 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.SecureBERT~2.0-base (ft).dnrti | {"strict_F1": 0.8192, "relaxed_F1": 0.881, "ci95_strict": [0.7938, 0.8439]} | E2_ft/securebert20_*_coarse_s13 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.SecureBERT~2.0-base (ft).cyner | {"strict_F1": 0.7257, "relaxed_F1": 0.8321, "ci95_strict": [0.6831, 0.7653]} | E2_ft/securebert20_*_coarse_s13 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.SecureBERT~2.0-base (ft).annoctr | {"strict_F1": 0.6595, "relaxed_F1": 0.7095, "ci95_strict": [0.6234, 0.6937]} | E2_ft/securebert20_*_coarse_s13 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.SecureBERT~2.0-base (ft).attacker | {"strict_F1": 0.6803, "relaxed_F1": 0.7483, "ci95_strict": [0.5887, 0.7629]} | E2_ft/securebert20_*_coarse_s13 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.GLiNER-L v2.1 (0-shot).aptner | {"strict_F1": 0.4309, "relaxed_F1": 0.5004, "ci95_strict": [0.4081, 0.457]} | E3_zs/gliner_large | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.GLiNER-L v2.1 (0-shot).dnrti | {"strict_F1": 0.5025, "relaxed_F1": 0.6049, "ci95_strict": [0.4687, 0.5352]} | E3_zs/gliner_large | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.GLiNER-L v2.1 (0-shot).cyner | {"strict_F1": 0.4342, "relaxed_F1": 0.5876, "ci95_strict": [0.387, 0.4799]} | E3_zs/gliner_large | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.GLiNER-L v2.1 (0-shot).annoctr | {"strict_F1": 0.3798, "relaxed_F1": 0.4378, "ci95_strict": [0.3517, 0.4074]} | E3_zs/gliner_large | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.GLiNER-L v2.1 (0-shot).attacker | {"strict_F1": 0.3875, "relaxed_F1": 0.4438, "ci95_strict": [0.2934, 0.4872]} | E3_zs/gliner_large | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.NuNER-Zero (0-shot).aptner | {"strict_F1": 0.382, "relaxed_F1": 0.4374, "ci95_strict": [0.3606, 0.4071]} | E3_zs/nuner_zero | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.NuNER-Zero (0-shot).dnrti | {"strict_F1": 0.3606, "relaxed_F1": 0.6555, "ci95_strict": [0.3286, 0.393]} | E3_zs/nuner_zero | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.NuNER-Zero (0-shot).cyner | {"strict_F1": 0.3441, "relaxed_F1": 0.7496, "ci95_strict": [0.2872, 0.4013]} | E3_zs/nuner_zero | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.NuNER-Zero (0-shot).annoctr | {"strict_F1": 0.2181, "relaxed_F1": 0.3048, "ci95_strict": [0.1963, 0.2409]} | E3_zs/nuner_zero | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.NuNER-Zero (0-shot).attacker | {"strict_F1": 0.1645, "relaxed_F1": 0.4679, "ci95_strict": [0.1055, 0.2278]} | E3_zs/nuner_zero | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Qwen3-8B (0-shot).aptner | {"strict_F1": 0.4762, "relaxed_F1": 0.4961, "ci95_strict": [0.4508, 0.502]} | E4_llm/qwen3_8b_0shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Qwen3-8B (0-shot).dnrti | {"strict_F1": 0.4848, "relaxed_F1": 0.5766, "ci95_strict": [0.4508, 0.5186]} | E4_llm/qwen3_8b_0shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Qwen3-8B (0-shot).cyner | {"strict_F1": 0.4183, "relaxed_F1": 0.4805, "ci95_strict": [0.3597, 0.4806]} | E4_llm/qwen3_8b_0shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Qwen3-8B (0-shot).annoctr | {"strict_F1": 0.3801, "relaxed_F1": 0.4086, "ci95_strict": [0.3507, 0.4139]} | E4_llm/qwen3_8b_0shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Qwen3-8B (0-shot).attacker | {"strict_F1": 0.2742, "relaxed_F1": 0.3545, "ci95_strict": [0.1714, 0.3836]} | E4_llm/qwen3_8b_0shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Qwen3-8B (5-shot).aptner | {"strict_F1": 0.5513, "relaxed_F1": 0.5774, "ci95_strict": [0.5256, 0.5758]} | E4_llm/qwen3_8b_5shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Qwen3-8B (5-shot).dnrti | {"strict_F1": 0.492, "relaxed_F1": 0.5751, "ci95_strict": [0.4607, 0.5255]} | E4_llm/qwen3_8b_5shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Qwen3-8B (5-shot).cyner | {"strict_F1": 0.5208, "relaxed_F1": 0.6351, "ci95_strict": [0.468, 0.574]} | E4_llm/qwen3_8b_5shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Qwen3-8B (5-shot).annoctr | {"strict_F1": 0.4131, "relaxed_F1": 0.4445, "ci95_strict": [0.3845, 0.4409]} | E4_llm/qwen3_8b_5shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Qwen3-8B (5-shot).attacker | {"strict_F1": 0.2994, "relaxed_F1": 0.3616, "ci95_strict": [0.2286, 0.3728]} | E4_llm/qwen3_8b_5shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Foundation-Sec-8B-It (0-shot).aptner | {"strict_F1": 0.4242, "relaxed_F1": 0.4608, "ci95_strict": [0.3978, 0.4531]} | E4_llm/fsec8b_0shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Foundation-Sec-8B-It (0-shot).dnrti | {"strict_F1": 0.4513, "relaxed_F1": 0.5307, "ci95_strict": [0.4172, 0.484]} | E4_llm/fsec8b_0shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Foundation-Sec-8B-It (0-shot).cyner | {"strict_F1": 0.3323, "relaxed_F1": 0.3904, "ci95_strict": [0.2777, 0.3822]} | E4_llm/fsec8b_0shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Foundation-Sec-8B-It (0-shot).annoctr | {"strict_F1": 0.3443, "relaxed_F1": 0.3756, "ci95_strict": [0.3158, 0.3754]} | E4_llm/fsec8b_0shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Foundation-Sec-8B-It (0-shot).attacker | {"strict_F1": 0.2671, "relaxed_F1": 0.3151, "ci95_strict": [0.1603, 0.3812]} | E4_llm/fsec8b_0shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Foundation-Sec-8B-It (5-shot).aptner | {"strict_F1": 0.5767, "relaxed_F1": 0.6191, "ci95_strict": [0.5521, 0.6003]} | E4_llm/fsec8b_5shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Foundation-Sec-8B-It (5-shot).dnrti | {"strict_F1": 0.4956, "relaxed_F1": 0.5731, "ci95_strict": [0.464, 0.529]} | E4_llm/fsec8b_5shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Foundation-Sec-8B-It (5-shot).cyner | {"strict_F1": 0.4884, "relaxed_F1": 0.6, "ci95_strict": [0.4376, 0.5358]} | E4_llm/fsec8b_5shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Foundation-Sec-8B-It (5-shot).annoctr | {"strict_F1": 0.3496, "relaxed_F1": 0.3714, "ci95_strict": [0.3259, 0.374]} | E4_llm/fsec8b_5shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.Foundation-Sec-8B-It (5-shot).attacker | {"strict_F1": 0.3586, "relaxed_F1": 0.4293, "ci95_strict": [0.2786, 0.44]} | E4_llm/fsec8b_5shot | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.roberta_seeds.aptner | {"F1s": [0.6509, 0.6458, 0.6521], "mean": 0.6496000000000001, "sd": 0.002731300056749523} | E2_ft/roberta_aptner_coarse_s13|17|19 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.roberta_seeds.dnrti | {"F1s": [0.8406, 0.8275, 0.8297], "mean": 0.8326, "sd": 0.0057277104209855715} | E2_ft/roberta_dnrti_coarse_s13|17|19 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.roberta_seeds.cyner | {"F1s": [0.8171, 0.8113, 0.8251], "mean": 0.8178333333333333, "sd": 0.005657639869140533} | E2_ft/roberta_cyner_coarse_s13|17|19 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.roberta_seeds.annoctr | {"F1s": [0.6758, 0.6903, 0.6865], "mean": 0.6842, "sd": 0.006138946706615639} | E2_ft/roberta_annoctr_coarse_s13|17|19 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2.roberta_seeds.attacker | {"F1s": [0.642, 0.6351, 0.6599], "mean": 0.6456666666666667, "sd": 0.010451262549993148} | E2_ft/roberta_attacker_coarse_s13|17|19 | scripts/gold_ner/{finetune_ner,zeroshot_span_ner,llm_ner}.py |
| T2b.RoBERTa-base.aptner | {"strict_F1": 0.619, "relaxed_F1": 0.6981, "ci95_strict": [0.6009, 0.6383], "n_labels": 40} | E2_ft/roberta_aptner_fine_s13 |  |
| T2b.RoBERTa-base.dnrti | {"strict_F1": 0.8017, "relaxed_F1": 0.8641, "ci95_strict": [0.7833, 0.82], "n_labels": 27} | E2_ft/roberta_dnrti_fine_s13 |  |
| T2b.RoBERTa-base.cyner | {"strict_F1": 0.729, "relaxed_F1": 0.8148, "ci95_strict": [0.6973, 0.7602], "n_labels": 11} | E2_ft/roberta_cyner_fine_s13 |  |
| T2b.RoBERTa-base.annoctr | {"strict_F1": 0.644, "relaxed_F1": 0.7523, "ci95_strict": [0.6223, 0.6653], "n_labels": 23} | E2_ft/roberta_annoctr_fine_s13 |  |
| T2b.RoBERTa-base.attacker | {"strict_F1": 0.3935, "relaxed_F1": 0.6187, "ci95_strict": [0.3328, 0.4585], "n_labels": 37} | E2_ft/roberta_attacker_fine_s13 |  |
| T2b.DeBERTa-v3-base.aptner | {"strict_F1": 0.6249, "relaxed_F1": 0.7118, "ci95_strict": [0.6058, 0.6443], "n_labels": 40} | E2_ft/deberta-v3_aptner_fine_s13 |  |
| T2b.DeBERTa-v3-base.dnrti | {"strict_F1": 0.8149, "relaxed_F1": 0.8701, "ci95_strict": [0.7957, 0.8322], "n_labels": 27} | E2_ft/deberta-v3_dnrti_fine_s13 |  |
| T2b.DeBERTa-v3-base.cyner | {"strict_F1": 0.764, "relaxed_F1": 0.843, "ci95_strict": [0.7346, 0.794], "n_labels": 11} | E2_ft/deberta-v3_cyner_fine_s13 |  |
| T2b.DeBERTa-v3-base.annoctr | {"strict_F1": 0.6872, "relaxed_F1": 0.7808, "ci95_strict": [0.6691, 0.7048], "n_labels": 23} | E2_ft/deberta-v3_annoctr_fine_s13 |  |
| T2b.DeBERTa-v3-base.attacker | {"strict_F1": 0.3769, "relaxed_F1": 0.5895, "ci95_strict": [0.3146, 0.4399], "n_labels": 37} | E2_ft/deberta-v3_attacker_fine_s13 |  |
| T2b.SecureBERT~2.0-base.aptner | {"strict_F1": 0.5941, "relaxed_F1": 0.6866, "ci95_strict": [0.5706, 0.6178], "n_labels": 40} | E2_ft/securebert20_aptner_fine_s13 |  |
| T2b.SecureBERT~2.0-base.dnrti | {"strict_F1": 0.8501, "relaxed_F1": 0.9046, "ci95_strict": [0.8302, 0.8694], "n_labels": 27} | E2_ft/securebert20_dnrti_fine_s13 |  |
| T2b.SecureBERT~2.0-base.cyner | {"strict_F1": 0.6537, "relaxed_F1": 0.7814, "ci95_strict": [0.6197, 0.6871], "n_labels": 11} | E2_ft/securebert20_cyner_fine_s13 |  |
| T2b.SecureBERT~2.0-base.annoctr | {"strict_F1": 0.626, "relaxed_F1": 0.7428, "ci95_strict": [0.6067, 0.646], "n_labels": 23} | E2_ft/securebert20_annoctr_fine_s13 |  |
| T2b.SecureBERT~2.0-base.attacker | {"strict_F1": 0.4025, "relaxed_F1": 0.655, "ci95_strict": [0.3359, 0.4704], "n_labels": 37} | E2_ft/securebert20_attacker_fine_s13 |  |
| T3.roberta.aptner->aptner | {"value": 0.6509} | E2_ft/roberta_aptner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.aptner->dnrti | {"value": [0.6116, 0.404]} | E2_ft/roberta_aptner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.aptner->cyner | {"value": [0.6045, 0.2726]} | E2_ft/roberta_aptner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.aptner->annoctr | {"value": [0.4662, 0.2785]} | E2_ft/roberta_aptner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.aptner->attacker | {"value": [0.1971, 0.1837]} | E2_ft/roberta_aptner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.dnrti->aptner | {"value": [0.5694, 0.2361]} | E2_ft/roberta_dnrti_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.dnrti->dnrti | {"value": 0.8406} | E2_ft/roberta_dnrti_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.dnrti->cyner | {"value": [0.5882, 0.0077]} | E2_ft/roberta_dnrti_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.dnrti->annoctr | {"value": [0.4991, 0.1696]} | E2_ft/roberta_dnrti_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.dnrti->attacker | {"value": [0.324, 0.1774]} | E2_ft/roberta_dnrti_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.cyner->aptner | {"value": [0.6591, 0.2988]} | E2_ft/roberta_cyner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.cyner->dnrti | {"value": [0.5878, 0.0718]} | E2_ft/roberta_cyner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.cyner->cyner | {"value": 0.8171} | E2_ft/roberta_cyner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.cyner->annoctr | {"value": [0.5898, 0.103]} | E2_ft/roberta_cyner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.cyner->attacker | {"value": [0.2143, 0.1255]} | E2_ft/roberta_cyner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.annoctr->aptner | {"value": [0.4143, 0.3773]} | E2_ft/roberta_annoctr_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.annoctr->dnrti | {"value": [0.5791, 0.2958]} | E2_ft/roberta_annoctr_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.annoctr->cyner | {"value": [0.5479, 0.2559]} | E2_ft/roberta_annoctr_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.annoctr->annoctr | {"value": 0.6758} | E2_ft/roberta_annoctr_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.annoctr->attacker | {"value": [0.1692, 0.156]} | E2_ft/roberta_annoctr_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.attacker->aptner | {"value": [0.4229, 0.3933]} | E2_ft/roberta_attacker_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.attacker->dnrti | {"value": [0.5743, 0.3138]} | E2_ft/roberta_attacker_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.attacker->cyner | {"value": [0.213, 0.1626]} | E2_ft/roberta_attacker_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.attacker->annoctr | {"value": [0.282, 0.275]} | E2_ft/roberta_attacker_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.roberta.attacker->attacker | {"value": 0.642} | E2_ft/roberta_attacker_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.aptner->aptner | {"value": 0.6668} | E2_ft/deberta-v3_aptner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.aptner->dnrti | {"value": [0.6048, 0.4016]} | E2_ft/deberta-v3_aptner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.aptner->cyner | {"value": [0.6654, 0.2873]} | E2_ft/deberta-v3_aptner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.aptner->annoctr | {"value": [0.46, 0.2952]} | E2_ft/deberta-v3_aptner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.aptner->attacker | {"value": [0.2123, 0.2006]} | E2_ft/deberta-v3_aptner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.dnrti->aptner | {"value": [0.5966, 0.2464]} | E2_ft/deberta-v3_dnrti_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.dnrti->dnrti | {"value": 0.8386} | E2_ft/deberta-v3_dnrti_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.dnrti->cyner | {"value": [0.5882, 0.0079]} | E2_ft/deberta-v3_dnrti_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.dnrti->annoctr | {"value": [0.4689, 0.1565]} | E2_ft/deberta-v3_dnrti_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.dnrti->attacker | {"value": [0.2976, 0.1582]} | E2_ft/deberta-v3_dnrti_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.cyner->aptner | {"value": [0.6872, 0.314]} | E2_ft/deberta-v3_cyner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.cyner->dnrti | {"value": [0.5512, 0.0772]} | E2_ft/deberta-v3_cyner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.cyner->cyner | {"value": 0.8528} | E2_ft/deberta-v3_cyner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.cyner->annoctr | {"value": [0.5911, 0.1018]} | E2_ft/deberta-v3_cyner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.cyner->attacker | {"value": [0.2323, 0.1417]} | E2_ft/deberta-v3_cyner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.annoctr->aptner | {"value": [0.3876, 0.3532]} | E2_ft/deberta-v3_annoctr_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.annoctr->dnrti | {"value": [0.6082, 0.3063]} | E2_ft/deberta-v3_annoctr_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.annoctr->cyner | {"value": [0.7033, 0.3435]} | E2_ft/deberta-v3_annoctr_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.annoctr->annoctr | {"value": 0.7012} | E2_ft/deberta-v3_annoctr_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.annoctr->attacker | {"value": [0.1801, 0.1667]} | E2_ft/deberta-v3_annoctr_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.attacker->aptner | {"value": [0.4139, 0.3859]} | E2_ft/deberta-v3_attacker_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.attacker->dnrti | {"value": [0.5858, 0.334]} | E2_ft/deberta-v3_attacker_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.attacker->cyner | {"value": [0.2618, 0.1931]} | E2_ft/deberta-v3_attacker_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.attacker->annoctr | {"value": [0.2614, 0.2576]} | E2_ft/deberta-v3_attacker_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.deberta-v3.attacker->attacker | {"value": 0.6361} | E2_ft/deberta-v3_attacker_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.aptner->aptner | {"value": 0.6313} | E2_ft/securebert20_aptner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.aptner->dnrti | {"value": [0.7147, 0.4914]} | E2_ft/securebert20_aptner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.aptner->cyner | {"value": [0.4413, 0.1694]} | E2_ft/securebert20_aptner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.aptner->annoctr | {"value": [0.3432, 0.1568]} | E2_ft/securebert20_aptner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.aptner->attacker | {"value": [0.1831, 0.1687]} | E2_ft/securebert20_aptner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.dnrti->aptner | {"value": [0.589, 0.2377]} | E2_ft/securebert20_dnrti_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.dnrti->dnrti | {"value": 0.8192} | E2_ft/securebert20_dnrti_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.dnrti->cyner | {"value": [0.5263, 0.0083]} | E2_ft/securebert20_dnrti_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.dnrti->annoctr | {"value": [0.425, 0.1182]} | E2_ft/securebert20_dnrti_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.dnrti->attacker | {"value": [0.1829, 0.1014]} | E2_ft/securebert20_dnrti_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.cyner->aptner | {"value": [0.596, 0.2562]} | E2_ft/securebert20_cyner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.cyner->dnrti | {"value": [0.6582, 0.0856]} | E2_ft/securebert20_cyner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.cyner->cyner | {"value": 0.7257} | E2_ft/securebert20_cyner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.cyner->annoctr | {"value": [0.475, 0.0548]} | E2_ft/securebert20_cyner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.cyner->attacker | {"value": [0.176, 0.0982]} | E2_ft/securebert20_cyner_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.annoctr->aptner | {"value": [0.4001, 0.3626]} | E2_ft/securebert20_annoctr_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.annoctr->dnrti | {"value": [0.5861, 0.3097]} | E2_ft/securebert20_annoctr_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.annoctr->cyner | {"value": [0.1869, 0.0767]} | E2_ft/securebert20_annoctr_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.annoctr->annoctr | {"value": 0.6595} | E2_ft/securebert20_annoctr_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.annoctr->attacker | {"value": [0.153, 0.14]} | E2_ft/securebert20_annoctr_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.attacker->aptner | {"value": [0.3988, 0.371]} | E2_ft/securebert20_attacker_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.attacker->dnrti | {"value": [0.5309, 0.3118]} | E2_ft/securebert20_attacker_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.attacker->cyner | {"value": [0.1798, 0.1425]} | E2_ft/securebert20_attacker_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.attacker->annoctr | {"value": [0.2348, 0.2315]} | E2_ft/securebert20_attacker_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T3.securebert20.attacker->attacker | {"value": 0.6803} | E2_ft/securebert20_attacker_coarse_s13 | scripts/gold_ner/finetune_ner.py |
| T4.gazetteer.aptner__bt-ru | {"strict_F1": 0.1949, "relaxed_F1": 0.1949, "ci95_strict": [0.1662, 0.224]} | E5_noise/gazetteer_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.aptner__bt-de | {"strict_F1": 0.2083, "relaxed_F1": 0.2083, "ci95_strict": [0.1802, 0.2371]} | E5_noise/gazetteer_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.aptner__bt-zh | {"strict_F1": 0.2005, "relaxed_F1": 0.2005, "ci95_strict": [0.1677, 0.2327]} | E5_noise/gazetteer_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.aptner__bt-es | {"strict_F1": 0.2268, "relaxed_F1": 0.2268, "ci95_strict": [0.1998, 0.2581]} | E5_noise/gazetteer_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.aptner__defang | {"strict_F1": 0.1784, "relaxed_F1": 0.1784, "ci95_strict": [0.1488, 0.21]} | E5_noise/gazetteer_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.aptner__boiler | {"strict_F1": 0.2461, "relaxed_F1": 0.2474, "ci95_strict": [0.2138, 0.2772]} | E5_noise/gazetteer_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.aptner__lower | {"strict_F1": 0.2436, "relaxed_F1": 0.2436, "ci95_strict": [0.2099, 0.2761]} | E5_noise/gazetteer_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.aptner__typo | {"strict_F1": 0.2429, "relaxed_F1": 0.2429, "ci95_strict": [0.2107, 0.2779]} | E5_noise/gazetteer_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.aptner__bt-ru | {"strict_F1": 0.5322, "relaxed_F1": 0.5813, "ci95_strict": [0.5064, 0.5579]} | E5_noise/roberta_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.aptner__bt-de | {"strict_F1": 0.6204, "relaxed_F1": 0.6819, "ci95_strict": [0.6002, 0.6417]} | E5_noise/roberta_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.aptner__bt-zh | {"strict_F1": 0.5234, "relaxed_F1": 0.5692, "ci95_strict": [0.4977, 0.5511]} | E5_noise/roberta_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.aptner__bt-es | {"strict_F1": 0.6109, "relaxed_F1": 0.6665, "ci95_strict": [0.5895, 0.632]} | E5_noise/roberta_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.aptner__defang | {"strict_F1": 0.6357, "relaxed_F1": 0.6925, "ci95_strict": [0.6148, 0.6583]} | E5_noise/roberta_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.aptner__boiler | {"strict_F1": 0.6151, "relaxed_F1": 0.671, "ci95_strict": [0.5923, 0.637]} | E5_noise/roberta_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.aptner__lower | {"strict_F1": 0.4826, "relaxed_F1": 0.5095, "ci95_strict": [0.4578, 0.5103]} | E5_noise/roberta_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.aptner__typo | {"strict_F1": 0.6375, "relaxed_F1": 0.6927, "ci95_strict": [0.6167, 0.6587]} | E5_noise/roberta_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.aptner__bt-ru | {"strict_F1": 0.5384, "relaxed_F1": 0.5808, "ci95_strict": [0.5121, 0.5624]} | E5_noise/deberta-v3_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.aptner__bt-de | {"strict_F1": 0.6272, "relaxed_F1": 0.6857, "ci95_strict": [0.6065, 0.6503]} | E5_noise/deberta-v3_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.aptner__bt-zh | {"strict_F1": 0.5288, "relaxed_F1": 0.5751, "ci95_strict": [0.5017, 0.5544]} | E5_noise/deberta-v3_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.aptner__bt-es | {"strict_F1": 0.6205, "relaxed_F1": 0.6702, "ci95_strict": [0.5999, 0.6429]} | E5_noise/deberta-v3_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.aptner__defang | {"strict_F1": 0.653, "relaxed_F1": 0.714, "ci95_strict": [0.6299, 0.6767]} | E5_noise/deberta-v3_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.aptner__boiler | {"strict_F1": 0.6416, "relaxed_F1": 0.6985, "ci95_strict": [0.6188, 0.6641]} | E5_noise/deberta-v3_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.aptner__lower | {"strict_F1": 0.4948, "relaxed_F1": 0.5404, "ci95_strict": [0.4713, 0.52]} | E5_noise/deberta-v3_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.aptner__typo | {"strict_F1": 0.6534, "relaxed_F1": 0.7158, "ci95_strict": [0.6317, 0.6771]} | E5_noise/deberta-v3_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.aptner__bt-ru | {"strict_F1": 0.5072, "relaxed_F1": 0.5595, "ci95_strict": [0.4813, 0.5327]} | E5_noise/securebert20_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.aptner__bt-de | {"strict_F1": 0.5998, "relaxed_F1": 0.6655, "ci95_strict": [0.5779, 0.6223]} | E5_noise/securebert20_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.aptner__bt-zh | {"strict_F1": 0.4943, "relaxed_F1": 0.5426, "ci95_strict": [0.4688, 0.5228]} | E5_noise/securebert20_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.aptner__bt-es | {"strict_F1": 0.5957, "relaxed_F1": 0.6554, "ci95_strict": [0.5728, 0.6199]} | E5_noise/securebert20_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.aptner__defang | {"strict_F1": 0.6267, "relaxed_F1": 0.694, "ci95_strict": [0.604, 0.6504]} | E5_noise/securebert20_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.aptner__boiler | {"strict_F1": 0.6158, "relaxed_F1": 0.6782, "ci95_strict": [0.5936, 0.6397]} | E5_noise/securebert20_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.aptner__lower | {"strict_F1": 0.473, "relaxed_F1": 0.5206, "ci95_strict": [0.4498, 0.4995]} | E5_noise/securebert20_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.aptner__typo | {"strict_F1": 0.6267, "relaxed_F1": 0.692, "ci95_strict": [0.6057, 0.6499]} | E5_noise/securebert20_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.aptner__bt-ru | {"strict_F1": 0.3337, "relaxed_F1": 0.3819, "ci95_strict": [0.311, 0.36]} | E5_noise/gliner_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.aptner__bt-de | {"strict_F1": 0.4088, "relaxed_F1": 0.4853, "ci95_strict": [0.3865, 0.4334]} | E5_noise/gliner_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.aptner__bt-zh | {"strict_F1": 0.2906, "relaxed_F1": 0.3539, "ci95_strict": [0.2649, 0.3164]} | E5_noise/gliner_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.aptner__bt-es | {"strict_F1": 0.4112, "relaxed_F1": 0.4845, "ci95_strict": [0.3889, 0.4359]} | E5_noise/gliner_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.aptner__defang | {"strict_F1": 0.4103, "relaxed_F1": 0.48, "ci95_strict": [0.3881, 0.4352]} | E5_noise/gliner_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.aptner__boiler | {"strict_F1": 0.4076, "relaxed_F1": 0.4718, "ci95_strict": [0.3854, 0.4325]} | E5_noise/gliner_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.aptner__lower | {"strict_F1": 0.4066, "relaxed_F1": 0.4798, "ci95_strict": [0.3842, 0.4317]} | E5_noise/gliner_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.aptner__typo | {"strict_F1": 0.43, "relaxed_F1": 0.5008, "ci95_strict": [0.4069, 0.4555]} | E5_noise/gliner_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.aptner__bt-ru | {"strict_F1": 0.3595, "relaxed_F1": 0.3854, "ci95_strict": [0.3304, 0.3891]} | E5_noise/qwen3_0shot_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.aptner__bt-de | {"strict_F1": 0.4405, "relaxed_F1": 0.4737, "ci95_strict": [0.4162, 0.4673]} | E5_noise/qwen3_0shot_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.aptner__bt-zh | {"strict_F1": 0.3299, "relaxed_F1": 0.3505, "ci95_strict": [0.2997, 0.3601]} | E5_noise/qwen3_0shot_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.aptner__bt-es | {"strict_F1": 0.4555, "relaxed_F1": 0.4748, "ci95_strict": [0.4309, 0.4806]} | E5_noise/qwen3_0shot_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.aptner__defang | {"strict_F1": 0.4771, "relaxed_F1": 0.4973, "ci95_strict": [0.4516, 0.5023]} | E5_noise/qwen3_0shot_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.aptner__boiler | {"strict_F1": 0.4221, "relaxed_F1": 0.4414, "ci95_strict": [0.3974, 0.4465]} | E5_noise/qwen3_0shot_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.aptner__lower | {"strict_F1": 0.4328, "relaxed_F1": 0.4612, "ci95_strict": [0.4077, 0.4595]} | E5_noise/qwen3_0shot_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.aptner__typo | {"strict_F1": 0.4728, "relaxed_F1": 0.4937, "ci95_strict": [0.4485, 0.4976]} | E5_noise/qwen3_0shot_aptner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.cyner__bt-ru | {"strict_F1": 0.0544, "relaxed_F1": 0.0544, "ci95_strict": [0.0202, 0.0926]} | E5_noise/gazetteer_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.cyner__bt-de | {"strict_F1": 0.1385, "relaxed_F1": 0.1528, "ci95_strict": [0.083, 0.1957]} | E5_noise/gazetteer_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.cyner__bt-zh | {"strict_F1": 0.0795, "relaxed_F1": 0.0795, "ci95_strict": [0.0109, 0.1702]} | E5_noise/gazetteer_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.cyner__bt-es | {"strict_F1": 0.1271, "relaxed_F1": 0.1383, "ci95_strict": [0.0779, 0.1882]} | E5_noise/gazetteer_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.cyner__defang | {"strict_F1": 0.1417, "relaxed_F1": 0.1417, "ci95_strict": [0.092, 0.1945]} | E5_noise/gazetteer_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.cyner__boiler | {"strict_F1": 0.1478, "relaxed_F1": 0.2075, "ci95_strict": [0.0998, 0.2033]} | E5_noise/gazetteer_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.cyner__lower | {"strict_F1": 0.1499, "relaxed_F1": 0.2105, "ci95_strict": [0.0976, 0.2033]} | E5_noise/gazetteer_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.cyner__typo | {"strict_F1": 0.1483, "relaxed_F1": 0.2082, "ci95_strict": [0.103, 0.2056]} | E5_noise/gazetteer_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.cyner__bt-ru | {"strict_F1": 0.4769, "relaxed_F1": 0.5138, "ci95_strict": [0.428, 0.5299]} | E5_noise/roberta_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.cyner__bt-de | {"strict_F1": 0.7342, "relaxed_F1": 0.7947, "ci95_strict": [0.6946, 0.7764]} | E5_noise/roberta_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.cyner__bt-zh | {"strict_F1": 0.3467, "relaxed_F1": 0.3581, "ci95_strict": [0.2808, 0.4171]} | E5_noise/roberta_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.cyner__bt-es | {"strict_F1": 0.7263, "relaxed_F1": 0.7579, "ci95_strict": [0.6892, 0.7686]} | E5_noise/roberta_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.cyner__defang | {"strict_F1": 0.8136, "relaxed_F1": 0.8902, "ci95_strict": [0.7814, 0.8465]} | E5_noise/roberta_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.cyner__boiler | {"strict_F1": 0.6223, "relaxed_F1": 0.7019, "ci95_strict": [0.5855, 0.6578]} | E5_noise/roberta_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.cyner__lower | {"strict_F1": 0.6425, "relaxed_F1": 0.7614, "ci95_strict": [0.5945, 0.6892]} | E5_noise/roberta_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.cyner__typo | {"strict_F1": 0.8, "relaxed_F1": 0.8721, "ci95_strict": [0.7657, 0.8347]} | E5_noise/roberta_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.cyner__bt-ru | {"strict_F1": 0.4993, "relaxed_F1": 0.5342, "ci95_strict": [0.4497, 0.5526]} | E5_noise/deberta-v3_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.cyner__bt-de | {"strict_F1": 0.7886, "relaxed_F1": 0.8376, "ci95_strict": [0.7525, 0.8249]} | E5_noise/deberta-v3_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.cyner__bt-zh | {"strict_F1": 0.3709, "relaxed_F1": 0.3901, "ci95_strict": [0.3039, 0.4408]} | E5_noise/deberta-v3_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.cyner__bt-es | {"strict_F1": 0.7651, "relaxed_F1": 0.8107, "ci95_strict": [0.7295, 0.8014]} | E5_noise/deberta-v3_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.cyner__defang | {"strict_F1": 0.852, "relaxed_F1": 0.9058, "ci95_strict": [0.8222, 0.8816]} | E5_noise/deberta-v3_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.cyner__boiler | {"strict_F1": 0.8022, "relaxed_F1": 0.9065, "ci95_strict": [0.7641, 0.8365]} | E5_noise/deberta-v3_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.cyner__lower | {"strict_F1": 0.7714, "relaxed_F1": 0.8271, "ci95_strict": [0.7275, 0.8091]} | E5_noise/deberta-v3_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.cyner__typo | {"strict_F1": 0.8427, "relaxed_F1": 0.8942, "ci95_strict": [0.814, 0.873]} | E5_noise/deberta-v3_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.cyner__bt-ru | {"strict_F1": 0.2361, "relaxed_F1": 0.2517, "ci95_strict": [0.1532, 0.3965]} | E5_noise/securebert20_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.cyner__bt-de | {"strict_F1": 0.2565, "relaxed_F1": 0.2808, "ci95_strict": [0.1712, 0.4106]} | E5_noise/securebert20_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.cyner__bt-zh | {"strict_F1": 0.2213, "relaxed_F1": 0.238, "ci95_strict": [0.1613, 0.2893]} | E5_noise/securebert20_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.cyner__bt-es | {"strict_F1": 0.6323, "relaxed_F1": 0.7085, "ci95_strict": [0.5873, 0.6812]} | E5_noise/securebert20_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.cyner__defang | {"strict_F1": 0.7269, "relaxed_F1": 0.8313, "ci95_strict": [0.6835, 0.7659]} | E5_noise/securebert20_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.cyner__boiler | {"strict_F1": 0.5695, "relaxed_F1": 0.6905, "ci95_strict": [0.516, 0.6179]} | E5_noise/securebert20_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.cyner__lower | {"strict_F1": 0.5391, "relaxed_F1": 0.6708, "ci95_strict": [0.4869, 0.5862]} | E5_noise/securebert20_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.cyner__typo | {"strict_F1": 0.7207, "relaxed_F1": 0.824, "ci95_strict": [0.676, 0.7591]} | E5_noise/securebert20_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.cyner__bt-ru | {"strict_F1": 0.3484, "relaxed_F1": 0.4232, "ci95_strict": [0.2988, 0.3989]} | E5_noise/gliner_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.cyner__bt-de | {"strict_F1": 0.429, "relaxed_F1": 0.5472, "ci95_strict": [0.3775, 0.4759]} | E5_noise/gliner_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.cyner__bt-zh | {"strict_F1": 0.2607, "relaxed_F1": 0.2942, "ci95_strict": [0.2055, 0.3201]} | E5_noise/gliner_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.cyner__bt-es | {"strict_F1": 0.4186, "relaxed_F1": 0.5302, "ci95_strict": [0.3716, 0.4628]} | E5_noise/gliner_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.cyner__defang | {"strict_F1": 0.4325, "relaxed_F1": 0.5702, "ci95_strict": [0.3836, 0.4787]} | E5_noise/gliner_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.cyner__boiler | {"strict_F1": 0.399, "relaxed_F1": 0.552, "ci95_strict": [0.3503, 0.4459]} | E5_noise/gliner_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.cyner__lower | {"strict_F1": 0.4194, "relaxed_F1": 0.5753, "ci95_strict": [0.3697, 0.4683]} | E5_noise/gliner_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.cyner__typo | {"strict_F1": 0.4376, "relaxed_F1": 0.5863, "ci95_strict": [0.3899, 0.4845]} | E5_noise/gliner_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.cyner__bt-ru | {"strict_F1": 0.2351, "relaxed_F1": 0.2619, "ci95_strict": [0.1883, 0.2853]} | E5_noise/qwen3_0shot_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.cyner__bt-de | {"strict_F1": 0.3832, "relaxed_F1": 0.4349, "ci95_strict": [0.3237, 0.4469]} | E5_noise/qwen3_0shot_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.cyner__bt-zh | {"strict_F1": 0.208, "relaxed_F1": 0.2345, "ci95_strict": [0.1473, 0.2729]} | E5_noise/qwen3_0shot_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.cyner__bt-es | {"strict_F1": 0.3632, "relaxed_F1": 0.4208, "ci95_strict": [0.3098, 0.4188]} | E5_noise/qwen3_0shot_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.cyner__defang | {"strict_F1": 0.4199, "relaxed_F1": 0.4824, "ci95_strict": [0.3604, 0.4833]} | E5_noise/qwen3_0shot_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.cyner__boiler | {"strict_F1": 0.4027, "relaxed_F1": 0.4676, "ci95_strict": [0.3473, 0.4572]} | E5_noise/qwen3_0shot_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.cyner__lower | {"strict_F1": 0.3816, "relaxed_F1": 0.4756, "ci95_strict": [0.3262, 0.4357]} | E5_noise/qwen3_0shot_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.cyner__typo | {"strict_F1": 0.4183, "relaxed_F1": 0.4818, "ci95_strict": [0.3633, 0.4744]} | E5_noise/qwen3_0shot_cyner | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.annoctr__bt-ru | {"strict_F1": 0.2664, "relaxed_F1": 0.2684, "ci95_strict": [0.2298, 0.3048]} | E5_noise/gazetteer_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.annoctr__bt-de | {"strict_F1": 0.3378, "relaxed_F1": 0.3547, "ci95_strict": [0.3044, 0.373]} | E5_noise/gazetteer_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.annoctr__bt-zh | {"strict_F1": 0.245, "relaxed_F1": 0.255, "ci95_strict": [0.2067, 0.2863]} | E5_noise/gazetteer_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.annoctr__bt-es | {"strict_F1": 0.3201, "relaxed_F1": 0.3357, "ci95_strict": [0.2866, 0.351]} | E5_noise/gazetteer_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.annoctr__defang | {"strict_F1": 0.3743, "relaxed_F1": 0.4006, "ci95_strict": [0.3363, 0.4081]} | E5_noise/gazetteer_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.annoctr__boiler | {"strict_F1": 0.3031, "relaxed_F1": 0.3242, "ci95_strict": [0.27, 0.3341]} | E5_noise/gazetteer_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.annoctr__lower | {"strict_F1": 0.3047, "relaxed_F1": 0.3262, "ci95_strict": [0.2743, 0.3374]} | E5_noise/gazetteer_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gazetteer.annoctr__typo | {"strict_F1": 0.3022, "relaxed_F1": 0.3235, "ci95_strict": [0.2692, 0.3333]} | E5_noise/gazetteer_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.annoctr__bt-ru | {"strict_F1": 0.5131, "relaxed_F1": 0.524, "ci95_strict": [0.4682, 0.5532]} | E5_noise/roberta_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.annoctr__bt-de | {"strict_F1": 0.6253, "relaxed_F1": 0.6624, "ci95_strict": [0.5906, 0.6597]} | E5_noise/roberta_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.annoctr__bt-zh | {"strict_F1": 0.5685, "relaxed_F1": 0.582, "ci95_strict": [0.5249, 0.6104]} | E5_noise/roberta_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.annoctr__bt-es | {"strict_F1": 0.6323, "relaxed_F1": 0.6625, "ci95_strict": [0.5969, 0.6662]} | E5_noise/roberta_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.annoctr__defang | {"strict_F1": 0.6576, "relaxed_F1": 0.6986, "ci95_strict": [0.6256, 0.6897]} | E5_noise/roberta_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.annoctr__boiler | {"strict_F1": 0.638, "relaxed_F1": 0.6772, "ci95_strict": [0.606, 0.6696]} | E5_noise/roberta_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.annoctr__lower | {"strict_F1": 0.3723, "relaxed_F1": 0.4391, "ci95_strict": [0.3289, 0.4108]} | E5_noise/roberta_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.roberta.annoctr__typo | {"strict_F1": 0.6433, "relaxed_F1": 0.6851, "ci95_strict": [0.6103, 0.674]} | E5_noise/roberta_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.annoctr__bt-ru | {"strict_F1": 0.5464, "relaxed_F1": 0.5603, "ci95_strict": [0.507, 0.5857]} | E5_noise/deberta-v3_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.annoctr__bt-de | {"strict_F1": 0.6322, "relaxed_F1": 0.6671, "ci95_strict": [0.5956, 0.6676]} | E5_noise/deberta-v3_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.annoctr__bt-zh | {"strict_F1": 0.56, "relaxed_F1": 0.5708, "ci95_strict": [0.5176, 0.6026]} | E5_noise/deberta-v3_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.annoctr__bt-es | {"strict_F1": 0.6399, "relaxed_F1": 0.6653, "ci95_strict": [0.6057, 0.6721]} | E5_noise/deberta-v3_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.annoctr__defang | {"strict_F1": 0.6837, "relaxed_F1": 0.7276, "ci95_strict": [0.6535, 0.7154]} | E5_noise/deberta-v3_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.annoctr__boiler | {"strict_F1": 0.6587, "relaxed_F1": 0.7063, "ci95_strict": [0.6255, 0.6898]} | E5_noise/deberta-v3_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.annoctr__lower | {"strict_F1": 0.3355, "relaxed_F1": 0.3914, "ci95_strict": [0.2955, 0.3789]} | E5_noise/deberta-v3_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.deberta-v3.annoctr__typo | {"strict_F1": 0.6759, "relaxed_F1": 0.7205, "ci95_strict": [0.6457, 0.7081]} | E5_noise/deberta-v3_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.annoctr__bt-ru | {"strict_F1": 0.5526, "relaxed_F1": 0.5632, "ci95_strict": [0.508, 0.5949]} | E5_noise/securebert20_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.annoctr__bt-de | {"strict_F1": 0.6377, "relaxed_F1": 0.6741, "ci95_strict": [0.6, 0.6765]} | E5_noise/securebert20_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.annoctr__bt-zh | {"strict_F1": 0.2258, "relaxed_F1": 0.235, "ci95_strict": [0.1438, 0.4239]} | E5_noise/securebert20_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.annoctr__bt-es | {"strict_F1": 0.6169, "relaxed_F1": 0.6446, "ci95_strict": [0.5792, 0.6533]} | E5_noise/securebert20_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.annoctr__defang | {"strict_F1": 0.6477, "relaxed_F1": 0.6964, "ci95_strict": [0.6124, 0.6819]} | E5_noise/securebert20_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.annoctr__boiler | {"strict_F1": 0.6039, "relaxed_F1": 0.6555, "ci95_strict": [0.5694, 0.6367]} | E5_noise/securebert20_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.annoctr__lower | {"strict_F1": 0.2474, "relaxed_F1": 0.2876, "ci95_strict": [0.2078, 0.2865]} | E5_noise/securebert20_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.securebert20.annoctr__typo | {"strict_F1": 0.6424, "relaxed_F1": 0.6937, "ci95_strict": [0.6078, 0.6764]} | E5_noise/securebert20_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.annoctr__bt-ru | {"strict_F1": 0.2411, "relaxed_F1": 0.2638, "ci95_strict": [0.2145, 0.2663]} | E5_noise/gliner_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.annoctr__bt-de | {"strict_F1": 0.3448, "relaxed_F1": 0.3823, "ci95_strict": [0.3165, 0.3727]} | E5_noise/gliner_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.annoctr__bt-zh | {"strict_F1": 0.2305, "relaxed_F1": 0.2516, "ci95_strict": [0.2004, 0.2615]} | E5_noise/gliner_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.annoctr__bt-es | {"strict_F1": 0.3612, "relaxed_F1": 0.3985, "ci95_strict": [0.3347, 0.3876]} | E5_noise/gliner_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.annoctr__defang | {"strict_F1": 0.3763, "relaxed_F1": 0.4348, "ci95_strict": [0.3482, 0.4043]} | E5_noise/gliner_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.annoctr__boiler | {"strict_F1": 0.3203, "relaxed_F1": 0.3675, "ci95_strict": [0.2961, 0.347]} | E5_noise/gliner_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.annoctr__lower | {"strict_F1": 0.3317, "relaxed_F1": 0.3861, "ci95_strict": [0.3035, 0.3584]} | E5_noise/gliner_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.gliner.annoctr__typo | {"strict_F1": 0.3654, "relaxed_F1": 0.421, "ci95_strict": [0.3374, 0.3921]} | E5_noise/gliner_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.annoctr__bt-ru | {"strict_F1": 0.273, "relaxed_F1": 0.2937, "ci95_strict": [0.2434, 0.3013]} | E5_noise/qwen3_0shot_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.annoctr__bt-de | {"strict_F1": 0.3665, "relaxed_F1": 0.3964, "ci95_strict": [0.3378, 0.3943]} | E5_noise/qwen3_0shot_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.annoctr__bt-zh | {"strict_F1": 0.2842, "relaxed_F1": 0.2936, "ci95_strict": [0.252, 0.319]} | E5_noise/qwen3_0shot_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.annoctr__bt-es | {"strict_F1": 0.3736, "relaxed_F1": 0.3951, "ci95_strict": [0.3438, 0.4027]} | E5_noise/qwen3_0shot_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.annoctr__defang | {"strict_F1": 0.3853, "relaxed_F1": 0.415, "ci95_strict": [0.3575, 0.4156]} | E5_noise/qwen3_0shot_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.annoctr__boiler | {"strict_F1": 0.2914, "relaxed_F1": 0.3115, "ci95_strict": [0.268, 0.3178]} | E5_noise/qwen3_0shot_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.annoctr__lower | {"strict_F1": 0.3669, "relaxed_F1": 0.4053, "ci95_strict": [0.3393, 0.3965]} | E5_noise/qwen3_0shot_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T4.qwen3_0shot.annoctr__typo | {"strict_F1": 0.3778, "relaxed_F1": 0.4041, "ci95_strict": [0.3509, 0.4088]} | E5_noise/qwen3_0shot_annoctr | scripts/noise/make_noisy_sets.py + run_E5_eval.sh |
| T5.keyword(thesis).easy(wikipedia) | {"F1": 0.9185, "FPR": 0.062, "P": 0.9357, "R": 0.902, "ci95": {"F1": [0.9001, 0.9348], "FPR": [0.042, 0.084]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.keyword(thesis).hard(serverfault) | {"F1": 0.7968, "FPR": 0.362, "P": 0.7136, "R": 0.902, "ci95": {"F1": [0.7775, 0.8167], "FPR": [0.32, 0.404]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.keyword(thesis).hard(superuser) | {"F1": 0.82, "FPR": 0.298, "P": 0.7517, "R": 0.902, "ci95": {"F1": [0.7993, 0.8395], "FPR": [0.258, 0.34]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.nli(deberta-v3-zs, thr=0.7 config).easy(wikipedia) | {"F1": 0.9669, "FPR": 0.0, "P": 1.0, "R": 0.936, "ci95": {"F1": [0.9551, 0.9785], "FPR": [0.0, 0.0]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.nli(deberta-v3-zs, thr=0.7 config).hard(serverfault) | {"F1": 0.9332, "FPR": 0.07, "P": 0.9304, "R": 0.936, "ci95": {"F1": [0.9172, 0.9481], "FPR": [0.05, 0.094]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.nli(deberta-v3-zs, thr=0.7 config).hard(superuser) | {"F1": 0.9455, "FPR": 0.044, "P": 0.9551, "R": 0.936, "ci95": {"F1": [0.9314, 0.9594], "FPR": [0.028, 0.062]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.nli(deberta-v3-zs, thr=0.65 dev-opt).easy(wikipedia) | {"F1": 0.9733, "FPR": 0.0, "P": 1.0, "R": 0.948, "ci95": {"F1": [0.9627, 0.9827], "FPR": [0.0, 0.0]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.nli(deberta-v3-zs, thr=0.65 dev-opt).hard(serverfault) | {"F1": 0.9358, "FPR": 0.078, "P": 0.924, "R": 0.948, "ci95": {"F1": [0.9209, 0.9505], "FPR": [0.056, 0.102]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.nli(deberta-v3-zs, thr=0.65 dev-opt).hard(superuser) | {"F1": 0.948, "FPR": 0.052, "P": 0.948, "R": 0.948, "ci95": {"F1": [0.9332, 0.9614], "FPR": [0.034, 0.072]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.ft-roberta(pos vs wikipedia).easy(wikipedia) | {"F1": 1.0, "FPR": 0.0, "P": 1.0, "R": 1.0, "ci95": {"F1": [1.0, 1.0], "FPR": [0.0, 0.0]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.ft-roberta(pos vs wikipedia).hard(serverfault) | {"F1": 0.6667, "FPR": 1.0, "P": 0.5, "R": 1.0, "ci95": {"F1": [0.6667, 0.6667], "FPR": [1.0, 1.0]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.ft-roberta(pos vs wikipedia).hard(superuser) | {"F1": 0.6667, "FPR": 1.0, "P": 0.5, "R": 1.0, "ci95": {"F1": [0.6667, 0.6667], "FPR": [1.0, 1.0]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.ft-roberta(pos vs hard).easy(wikipedia) | {"F1": 0.8317, "FPR": 0.34, "P": 0.7372, "R": 0.954, "ci95": {"F1": [0.8131, 0.8501], "FPR": [0.298, 0.384]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.ft-roberta(pos vs hard).hard(serverfault) | {"F1": 0.9656, "FPR": 0.022, "P": 0.9775, "R": 0.954, "ci95": {"F1": [0.9538, 0.9761], "FPR": [0.01, 0.036]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.ft-roberta(pos vs hard).hard(superuser) | {"F1": 0.9695, "FPR": 0.014, "P": 0.9855, "R": 0.954, "ci95": {"F1": [0.9582, 0.9807], "FPR": [0.006, 0.024]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.ft-roberta(pos vs mixed).easy(wikipedia) | {"F1": 0.9659, "FPR": 0.0, "P": 1.0, "R": 0.934, "ci95": {"F1": [0.954, 0.9765], "FPR": [0.0, 0.0]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.ft-roberta(pos vs mixed).hard(serverfault) | {"F1": 0.9619, "FPR": 0.008, "P": 0.9915, "R": 0.934, "ci95": {"F1": [0.9489, 0.9736], "FPR": [0.002, 0.016]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| T5.ft-roberta(pos vs mixed).hard(superuser) | {"F1": 0.9599, "FPR": 0.012, "P": 0.9873, "R": 0.934, "ci95": {"F1": [0.9472, 0.9724], "FPR": [0.004, 0.022]}} | E6_relevance | scripts/relevance/relevance_eval_hard.py |
| KEV.extracted_unique | {"value": 6488} | THESIS_artifacts | runs/THESIS_artifacts/kev_overlap.json (thesis pipeline run) |
| KEV.in_kev | {"value": 1599} | THESIS_artifacts | runs/THESIS_artifacts/kev_overlap.json (thesis pipeline run) |
| KEV.circular_pct | {"value": 24.6} | THESIS_artifacts | runs/THESIS_artifacts/kev_overlap.json (thesis pipeline run) |
| KEV.noncircular_n | {"value": 130} | THESIS_artifacts | runs/THESIS_artifacts/kev_overlap.json (thesis pipeline run) |
| KEV.noncircular_den | {"value": 5019} | THESIS_artifacts | runs/THESIS_artifacts/kev_overlap.json (thesis pipeline run) |
| KEV.noncircular_pct | {"value": 2.6} | THESIS_artifacts | runs/THESIS_artifacts/kev_overlap.json (thesis pipeline run) |
| KEV.nvd_kev | {"value": 42} | THESIS_artifacts | runs/THESIS_artifacts/kev_overlap.json (thesis pipeline run) |
| KEV.nvd_unique | {"value": 4875} | THESIS_artifacts | runs/THESIS_artifacts/kev_overlap.json (thesis pipeline run) |
| KEV.nvd_pct | {"value": 0.9} | THESIS_artifacts | runs/THESIS_artifacts/kev_overlap.json (thesis pipeline run) |
| T8.hybrid.annoctr | {"gazetteer": 0.3031, "roberta": 0.6758, "gapfill": 0.6758, "override": 0.5259} | E7_hybrid/roberta_annoctr |  |
| T8.hybrid.aptner | {"gazetteer": 0.2429, "roberta": 0.6509, "gapfill": 0.6564, "override": 0.6723} | E7_hybrid/roberta_aptner |  |
| T8.hybrid.attacker | {"gazetteer": 0.117, "roberta": 0.642, "gapfill": 0.6303, "override": 0.623} | E7_hybrid/roberta_attacker |  |
| T8.hybrid.cyner | {"gazetteer": 0.1487, "roberta": 0.8171, "gapfill": 0.8157, "override": 0.5549} | E7_hybrid/roberta_cyner |  |
| T8.hybrid.dnrti | {"gazetteer": 0.25, "roberta": 0.8406, "gapfill": 0.8406, "override": 0.809} | E7_hybrid/roberta_dnrti |  |
| T9.aptner.bt-ru.HASH | {"orig_hits": 59, "bt_hits": 23, "bt_hits_not_in_orig": 23, "corrupted_share_of_bt_hits": 1.0} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-de.HASH | {"orig_hits": 59, "bt_hits": 22, "bt_hits_not_in_orig": 5, "corrupted_share_of_bt_hits": 0.227} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-zh.HASH | {"orig_hits": 59, "bt_hits": 13, "bt_hits_not_in_orig": 12, "corrupted_share_of_bt_hits": 0.923} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-es.HASH | {"orig_hits": 59, "bt_hits": 26, "bt_hits_not_in_orig": 7, "corrupted_share_of_bt_hits": 0.269} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-ru.IP | {"orig_hits": 45, "bt_hits": 20, "bt_hits_not_in_orig": 4, "corrupted_share_of_bt_hits": 0.2} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-de.IP | {"orig_hits": 45, "bt_hits": 33, "bt_hits_not_in_orig": 5, "corrupted_share_of_bt_hits": 0.152} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-zh.IP | {"orig_hits": 45, "bt_hits": 16, "bt_hits_not_in_orig": 5, "corrupted_share_of_bt_hits": 0.312} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-es.IP | {"orig_hits": 45, "bt_hits": 37, "bt_hits_not_in_orig": 1, "corrupted_share_of_bt_hits": 0.027} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-ru.CVE | {"orig_hits": 30, "bt_hits": 7, "bt_hits_not_in_orig": 0, "corrupted_share_of_bt_hits": 0.0} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-de.CVE | {"orig_hits": 30, "bt_hits": 31, "bt_hits_not_in_orig": 1, "corrupted_share_of_bt_hits": 0.032} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-zh.CVE | {"orig_hits": 30, "bt_hits": 28, "bt_hits_not_in_orig": 3, "corrupted_share_of_bt_hits": 0.107} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-es.CVE | {"orig_hits": 30, "bt_hits": 31, "bt_hits_not_in_orig": 1, "corrupted_share_of_bt_hits": 0.032} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-ru.EMAIL | {"orig_hits": 22, "bt_hits": 18, "bt_hits_not_in_orig": 13, "corrupted_share_of_bt_hits": 0.722} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-de.EMAIL | {"orig_hits": 22, "bt_hits": 18, "bt_hits_not_in_orig": 8, "corrupted_share_of_bt_hits": 0.444} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-zh.EMAIL | {"orig_hits": 22, "bt_hits": 17, "bt_hits_not_in_orig": 13, "corrupted_share_of_bt_hits": 0.765} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-es.EMAIL | {"orig_hits": 22, "bt_hits": 23, "bt_hits_not_in_orig": 0, "corrupted_share_of_bt_hits": 0.0} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-ru.URL | {"orig_hits": 17, "bt_hits": 17, "bt_hits_not_in_orig": 15, "corrupted_share_of_bt_hits": 0.882} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-de.URL | {"orig_hits": 17, "bt_hits": 15, "bt_hits_not_in_orig": 5, "corrupted_share_of_bt_hits": 0.333} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-zh.URL | {"orig_hits": 17, "bt_hits": 16, "bt_hits_not_in_orig": 15, "corrupted_share_of_bt_hits": 0.938} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-es.URL | {"orig_hits": 17, "bt_hits": 17, "bt_hits_not_in_orig": 6, "corrupted_share_of_bt_hits": 0.353} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-ru.DOMAIN | {"orig_hits": 56, "bt_hits": 50, "bt_hits_not_in_orig": 26, "corrupted_share_of_bt_hits": 0.52} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-de.DOMAIN | {"orig_hits": 56, "bt_hits": 56, "bt_hits_not_in_orig": 5, "corrupted_share_of_bt_hits": 0.089} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-zh.DOMAIN | {"orig_hits": 56, "bt_hits": 38, "bt_hits_not_in_orig": 24, "corrupted_share_of_bt_hits": 0.632} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.aptner.bt-es.DOMAIN | {"orig_hits": 56, "bt_hits": 59, "bt_hits_not_in_orig": 4, "corrupted_share_of_bt_hits": 0.068} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-ru.HASH | {"orig_hits": 24, "bt_hits": 10, "bt_hits_not_in_orig": 10, "corrupted_share_of_bt_hits": 1.0} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-de.HASH | {"orig_hits": 24, "bt_hits": 23, "bt_hits_not_in_orig": 5, "corrupted_share_of_bt_hits": 0.217} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-zh.HASH | {"orig_hits": 24, "bt_hits": 9, "bt_hits_not_in_orig": 9, "corrupted_share_of_bt_hits": 1.0} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-es.HASH | {"orig_hits": 24, "bt_hits": 21, "bt_hits_not_in_orig": 7, "corrupted_share_of_bt_hits": 0.333} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-ru.IP | {"orig_hits": 8, "bt_hits": 2, "bt_hits_not_in_orig": 2, "corrupted_share_of_bt_hits": 1.0} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-de.IP | {"orig_hits": 8, "bt_hits": 5, "bt_hits_not_in_orig": 1, "corrupted_share_of_bt_hits": 0.2} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-zh.IP | {"orig_hits": 8, "bt_hits": 4, "bt_hits_not_in_orig": 3, "corrupted_share_of_bt_hits": 0.75} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-es.IP | {"orig_hits": 8, "bt_hits": 6, "bt_hits_not_in_orig": 1, "corrupted_share_of_bt_hits": 0.167} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-ru.CVE | {"orig_hits": 5, "bt_hits": 1, "bt_hits_not_in_orig": 0, "corrupted_share_of_bt_hits": 0.0} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-de.CVE | {"orig_hits": 5, "bt_hits": 5, "bt_hits_not_in_orig": 0, "corrupted_share_of_bt_hits": 0.0} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-zh.CVE | {"orig_hits": 5, "bt_hits": 6, "bt_hits_not_in_orig": 1, "corrupted_share_of_bt_hits": 0.167} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-es.CVE | {"orig_hits": 5, "bt_hits": 5, "bt_hits_not_in_orig": 0, "corrupted_share_of_bt_hits": 0.0} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-ru.DOMAIN | {"orig_hits": 9, "bt_hits": 11, "bt_hits_not_in_orig": 8, "corrupted_share_of_bt_hits": 0.727} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-de.DOMAIN | {"orig_hits": 9, "bt_hits": 9, "bt_hits_not_in_orig": 0, "corrupted_share_of_bt_hits": 0.0} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-zh.DOMAIN | {"orig_hits": 9, "bt_hits": 22, "bt_hits_not_in_orig": 21, "corrupted_share_of_bt_hits": 0.955} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.cyner.bt-es.DOMAIN | {"orig_hits": 9, "bt_hits": 12, "bt_hits_not_in_orig": 5, "corrupted_share_of_bt_hits": 0.417} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.annoctr.bt-ru.HASH | {"orig_hits": 117, "bt_hits": 80, "bt_hits_not_in_orig": 54, "corrupted_share_of_bt_hits": 0.675} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.annoctr.bt-de.HASH | {"orig_hits": 117, "bt_hits": 82, "bt_hits_not_in_orig": 20, "corrupted_share_of_bt_hits": 0.244} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.annoctr.bt-zh.HASH | {"orig_hits": 117, "bt_hits": 48, "bt_hits_not_in_orig": 34, "corrupted_share_of_bt_hits": 0.708} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.annoctr.bt-es.HASH | {"orig_hits": 117, "bt_hits": 103, "bt_hits_not_in_orig": 18, "corrupted_share_of_bt_hits": 0.175} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.annoctr.bt-ru.IP | {"orig_hits": 64, "bt_hits": 45, "bt_hits_not_in_orig": 11, "corrupted_share_of_bt_hits": 0.244} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.annoctr.bt-de.IP | {"orig_hits": 64, "bt_hits": 59, "bt_hits_not_in_orig": 1, "corrupted_share_of_bt_hits": 0.017} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.annoctr.bt-zh.IP | {"orig_hits": 64, "bt_hits": 26, "bt_hits_not_in_orig": 5, "corrupted_share_of_bt_hits": 0.192} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.annoctr.bt-es.IP | {"orig_hits": 64, "bt_hits": 187, "bt_hits_not_in_orig": 130, "corrupted_share_of_bt_hits": 0.695} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.annoctr.bt-ru.DOMAIN | {"orig_hits": 257, "bt_hits": 233, "bt_hits_not_in_orig": 144, "corrupted_share_of_bt_hits": 0.618} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.annoctr.bt-de.DOMAIN | {"orig_hits": 257, "bt_hits": 231, "bt_hits_not_in_orig": 41, "corrupted_share_of_bt_hits": 0.177} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.annoctr.bt-zh.DOMAIN | {"orig_hits": 257, "bt_hits": 322, "bt_hits_not_in_orig": 238, "corrupted_share_of_bt_hits": 0.739} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T9.annoctr.bt-es.DOMAIN | {"orig_hits": 257, "bt_hits": 260, "bt_hits_not_in_orig": 30, "corrupted_share_of_bt_hits": 0.115} | E5_noise/make_sets + scripts/noise/ioc_corruption.py |  |
| T10.opus-mt.ru.b1 | {"hash_survive_fwd_rt": [20.4, 14.3], "hash_corrupt_share_rt": 43.5, "ip_survive_fwd_rt": [47.0, 42.7], "url_survive_rt": 17.6} | E8_mt_ioc |  |
| T10.opus-mt.ru.b4 | {"hash_survive_fwd_rt": [23.5, 16.8], "hash_corrupt_share_rt": 34.7, "ip_survive_fwd_rt": [54.7, 52.1], "url_survive_rt": 29.4} | E8_mt_ioc |  |
| T10.opus-mt.de.b1 | {"hash_survive_fwd_rt": [57.7, 47.4], "hash_corrupt_share_rt": 4.1, "ip_survive_fwd_rt": [84.6, 76.9], "url_survive_rt": 64.7} | E8_mt_ioc |  |
| T10.opus-mt.de.b4 | {"hash_survive_fwd_rt": [75.5, 63.8], "hash_corrupt_share_rt": 0.8, "ip_survive_fwd_rt": [88.9, 88.0], "url_survive_rt": 70.6} | E8_mt_ioc |  |
| T10.nllb-600M.ru.b1 | {"hash_survive_fwd_rt": [50.5, 49.0], "hash_corrupt_share_rt": 1.0, "ip_survive_fwd_rt": [97.4, 91.5], "url_survive_rt": 70.6} | E8_mt_ioc |  |
| T10.nllb-600M.ru.b4 | {"hash_survive_fwd_rt": [66.3, 66.8], "hash_corrupt_share_rt": 0.7, "ip_survive_fwd_rt": [99.1, 95.7], "url_survive_rt": 76.5} | E8_mt_ioc |  |
| T10.nllb-600M.de.b1 | {"hash_survive_fwd_rt": [45.4, 38.3], "hash_corrupt_share_rt": 2.5, "ip_survive_fwd_rt": [88.9, 67.5], "url_survive_rt": 35.3} | E8_mt_ioc |  |
| T10.nllb-600M.de.b4 | {"hash_survive_fwd_rt": [58.7, 51.0], "hash_corrupt_share_rt": 1.9, "ip_survive_fwd_rt": [96.6, 88.0], "url_survive_rt": 64.7} | E8_mt_ioc |  |
| T10.nllb-1.3B.ru.b1 | {"hash_survive_fwd_rt": [71.9, 47.4], "hash_corrupt_share_rt": 1.5, "ip_survive_fwd_rt": [96.6, 47.0], "url_survive_rt": 52.9} | E8_mt_ioc |  |
| T10.nllb-1.3B.de.b1 | {"hash_survive_fwd_rt": [71.9, 52.0], "hash_corrupt_share_rt": 0.0, "ip_survive_fwd_rt": [96.6, 29.1], "url_survive_rt": 58.8} | E8_mt_ioc |  |
| T10.nllb-3.3B.ru.b1 | {"hash_survive_fwd_rt": [72.4, 40.3], "hash_corrupt_share_rt": 4.2, "ip_survive_fwd_rt": [93.2, 36.8], "url_survive_rt": 52.9} | E8_mt_ioc |  |
| T10.nllb-3.3B.de.b1 | {"hash_survive_fwd_rt": [52.6, 32.1], "hash_corrupt_share_rt": 3.4, "ip_survive_fwd_rt": [46.2, 23.1], "url_survive_rt": 35.3} | E8_mt_ioc |  |
| T10.m2m100.ru.b1 | {"hash_survive_fwd_rt": [64.3, 63.3], "hash_corrupt_share_rt": 0.0, "ip_survive_fwd_rt": [94.0, 92.3], "url_survive_rt": 70.6} | E8_mt_ioc |  |
| T10.m2m100.de.b1 | {"hash_survive_fwd_rt": [79.6, 73.0], "hash_corrupt_share_rt": 0.0, "ip_survive_fwd_rt": [98.3, 96.6], "url_survive_rt": 82.4} | E8_mt_ioc |  |
| T10.masked.opus-mt.ru | {"placeholder_recovery_pct": 61.4, "hash_survive_rt": 55.6} | E8_mt_ioc |  |
| T10.masked.opus-mt.de | {"placeholder_recovery_pct": 90.3, "hash_survive_rt": 85.7} | E8_mt_ioc |  |
| T10.masked.nllb-600M.ru | {"placeholder_recovery_pct": 88.1, "hash_survive_rt": 78.1} | E8_mt_ioc |  |
| T10.masked.nllb-600M.de | {"placeholder_recovery_pct": 63.9, "hash_survive_rt": 62.2} | E8_mt_ioc |  |
| T10.masked.nllb-1.3B.ru | {"placeholder_recovery_pct": 75.3, "hash_survive_rt": 73.0} | E8_mt_ioc |  |
| T10.masked.nllb-1.3B.de | {"placeholder_recovery_pct": 71.3, "hash_survive_rt": 60.2} | E8_mt_ioc |  |
| T10.masked.nllb-3.3B.ru | {"placeholder_recovery_pct": 73.4, "hash_survive_rt": 78.1} | E8_mt_ioc |  |
| T10.masked.nllb-3.3B.de | {"placeholder_recovery_pct": 56.9, "hash_survive_rt": 63.8} | E8_mt_ioc |  |
| T10.masked.m2m100.ru | {"placeholder_recovery_pct": 80.3, "hash_survive_rt": 58.7} | E8_mt_ioc |  |
| T10.masked.m2m100.de | {"placeholder_recovery_pct": 94.3, "hash_survive_rt": 89.8} | E8_mt_ioc |  |
| T11.nllb-600M_de.IOC{i} | {"placeholders": 721, "recovered": 461, "pct": 63.9} | E8_mt_ioc/placeholder_styles |  |
| T11.nllb-600M_ru.IOC{i} | {"placeholders": 721, "recovered": 635, "pct": 88.1} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_de.IOC{i} | {"placeholders": 721, "recovered": 651, "pct": 90.3} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_ru.IOC{i} | {"placeholders": 721, "recovered": 443, "pct": 61.4} | E8_mt_ioc/placeholder_styles |  |
| T11.nllb-600M_de.XQZ{i} | {"placeholders": 721, "recovered": 513, "pct": 71.2} | E8_mt_ioc/placeholder_styles |  |
| T11.nllb-600M_ru.XQZ{i} | {"placeholders": 721, "recovered": 613, "pct": 85.0} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_de.XQZ{i} | {"placeholders": 721, "recovered": 647, "pct": 89.7} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_ru.XQZ{i} | {"placeholders": 721, "recovered": 656, "pct": 91.0} | E8_mt_ioc/placeholder_styles |  |
| T11.nllb-600M_de.bracket[IOC{i}] | {"placeholders": 721, "recovered": 346, "pct": 48.0} | E8_mt_ioc/placeholder_styles |  |
| T11.nllb-600M_ru.bracket[IOC{i}] | {"placeholders": 721, "recovered": 469, "pct": 65.0} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_de.bracket[IOC{i}] | {"placeholders": 721, "recovered": 584, "pct": 81.0} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_ru.bracket[IOC{i}] | {"placeholders": 721, "recovered": 219, "pct": 30.4} | E8_mt_ioc/placeholder_styles |  |
| T11.nllb-600M_de.angle<ioc{i}> | {"placeholders": 721, "recovered": 91, "pct": 12.6} | E8_mt_ioc/placeholder_styles |  |
| T11.nllb-600M_ru.angle<ioc{i}> | {"placeholders": 721, "recovered": 285, "pct": 39.5} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_de.angle<ioc{i}> | {"placeholders": 721, "recovered": 568, "pct": 78.8} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_ru.angle<ioc{i}> | {"placeholders": 721, "recovered": 616, "pct": 85.4} | E8_mt_ioc/placeholder_styles |  |
| T11.nllb-600M_de.hex-like | {"placeholders": 721, "recovered": 482, "pct": 66.9} | E8_mt_ioc/placeholder_styles |  |
| T11.nllb-600M_ru.hex-like | {"placeholders": 721, "recovered": 639, "pct": 88.6} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_de.hex-like | {"placeholders": 721, "recovered": 651, "pct": 90.3} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_ru.hex-like | {"placeholders": 721, "recovered": 352, "pct": 48.8} | E8_mt_ioc/placeholder_styles |  |
| T11.nllb-600M_de.digits{i} | {"placeholders": 721, "recovered": 418, "pct": 58.0} | E8_mt_ioc/placeholder_styles |  |
| T11.nllb-600M_ru.digits{i} | {"placeholders": 721, "recovered": 603, "pct": 83.6} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_de.digits{i} | {"placeholders": 721, "recovered": 666, "pct": 92.4} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_ru.digits{i} | {"placeholders": 721, "recovered": 275, "pct": 38.1} | E8_mt_ioc/placeholder_styles |  |
| T11.nllb-600M_de.word ZORKA{i} | {"placeholders": 721, "recovered": 458, "pct": 63.5} | E8_mt_ioc/placeholder_styles |  |
| T11.nllb-600M_ru.word ZORKA{i} | {"placeholders": 721, "recovered": 520, "pct": 72.1} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_de.word ZORKA{i} | {"placeholders": 721, "recovered": 643, "pct": 89.2} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_ru.word ZORKA{i} | {"placeholders": 721, "recovered": 625, "pct": 86.7} | E8_mt_ioc/placeholder_styles |  |
| T11.nllb-600M_de.placeholder_{i} | {"placeholders": 721, "recovered": 420, "pct": 58.3} | E8_mt_ioc/placeholder_styles |  |
| T11.nllb-600M_ru.placeholder_{i} | {"placeholders": 721, "recovered": 440, "pct": 61.0} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_de.placeholder_{i} | {"placeholders": 721, "recovered": 617, "pct": 85.6} | E8_mt_ioc/placeholder_styles |  |
| T11.opus-mt_ru.placeholder_{i} | {"placeholders": 721, "recovered": 486, "pct": 67.4} | E8_mt_ioc/placeholder_styles |  |

## KEV snapshot

- CISA KEV catalogVersion 2026.05.15 (1,592 entries, 1,611 unique CVE strings), retrieved 2026-05-16; overlap figures in runs/THESIS_artifacts/kev_overlap.json

## Gold mentions surviving back-translation verbatim (scripts/noise/make_noisy_sets.py, run E5_noise/make_sets)

| set | gold | dropped | dropped % |
|---|---|---|---|
| aptner__bt-ru | 2572 | 995 | 38.7 |
| cyner__bt-ru | 553 | 295 | 53.3 |
| annoctr__bt-ru | 875 | 383 | 43.8 |
| aptner__bt-de | 2572 | 279 | 10.8 |
| cyner__bt-de | 553 | 65 | 11.8 |
| annoctr__bt-de | 875 | 148 | 16.9 |
| aptner__bt-zh | 2572 | 1299 | 50.5 |
| cyner__bt-zh | 553 | 425 | 76.9 |
| annoctr__bt-zh | 875 | 479 | 54.7 |
| aptner__bt-es | 2572 | 239 | 9.3 |
| cyner__bt-es | 553 | 81 | 14.6 |
| annoctr__bt-es | 875 | 105 | 12.0 |
| aptner__defang | 2572 | 0 | 0.0 |
| cyner__defang | 553 | 0 | 0.0 |
| annoctr__defang | 875 | 1 | 0.1 |
| aptner__boiler | 2572 | 0 | 0.0 |
| cyner__boiler | 553 | 0 | 0.0 |
| annoctr__boiler | 875 | 1 | 0.1 |
| aptner__lower | 2572 | 0 | 0.0 |
| cyner__lower | 553 | 0 | 0.0 |
| annoctr__lower | 875 | 1 | 0.1 |
| aptner__typo | 2572 | 0 | 0.0 |
| cyner__typo | 553 | 0 | 0.0 |
| annoctr__typo | 875 | 1 | 0.1 |