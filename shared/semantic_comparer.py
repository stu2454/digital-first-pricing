"""
Semantic Comparer for PAPL Documents
Compares two parsed PAPL documents and identifies meaningful changes

REVAMPED VERSION (FLAT SIGNATURE MATCHING):

- Uses robust PAPLParser price extraction
- Flattens ALL prices from ALL pricing tables (no table matching)
- Matches prices by (item_number, column_label) signature
- Ignores table index / layout differences
- Provides summary stats for price changes
- Keeps existing rule/guidance/structure comparison
"""

from typing import Dict, List, Any, Optional, Tuple
from fuzzywuzzy import fuzz
import json


class SemanticComparer:
    """
    Compare PAPL documents semantically:
    - Price changes
    - Business rule changes
    - Guidance changes
    - Structural changes
    - Table changes
    """

    def __init__(self, similarity_threshold: int = 85, debug: bool = False):
        self.similarity_threshold = similarity_threshold
        self.debug = debug

    # ===============================================================
    # PUBLIC ENTRY POINT
    # ===============================================================
    def compare(self, old_doc_data: Dict[str, Any], new_doc_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.compare_with_price_detection(old_doc_data, new_doc_data)

    # ===============================================================
    # PRICE DETECTION + SEMANTIC COMPARISON
    # ===============================================================
    def compare_with_price_detection(
        self,
        old_doc_data: Dict[str, Any],
        new_doc_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        from papl_parser import PAPLParser

        parser = PAPLParser()

        if self.debug:
            print("\n" + "=" * 120)
            print("🔍 SEMANTIC COMPARER — PRICE + SEMANTIC COMPARISON")
            print("=" * 120)

            old_tables = old_doc_data.get("raw_tables", [])
            new_tables = new_doc_data.get("raw_tables", [])
            print(f"Comparer sees OLD tables: {len(old_tables)}")
            print(f"Comparer sees NEW tables: {len(new_tables)}")

            if old_tables:
                print("\nOLD HEADERS (first 5 tables):")
                for i, t in enumerate(old_tables[:5]):
                    hdr = [str(h) for h in t.get("data", [[]])[0]] if t.get("data") else []
                    print(f"  Table {i}: {hdr}")
            if new_tables:
                print("\nNEW HEADERS (first 5 tables):")
                for i, t in enumerate(new_tables[:5]):
                    hdr = [str(h) for h in t.get("data", [[]])[0]] if t.get("data") else []
                    print(f"  Table {i}: {hdr}")
            print()

        # STEP 1 — PRICE CHANGES (FLAT SIGNATURE-BASED MATCHING)
        price_changes = self._compare_all_prices_flat(
            old_doc_data.get("raw_tables", []),
            new_doc_data.get("raw_tables", []),
            parser,
        )

        # STEP 2 — SEMANTIC (NON-PRICE) CHANGES
        semantic_results = self._compare_semantic(old_doc_data, new_doc_data)

        # MERGE
        semantic_results["price_changes"] = {
            "count": len(price_changes),
            "changes": price_changes,
            "summary": self._summarize_price_changes(price_changes),
        }

        semantic_results["summary"]["total_price_changes"] = len(price_changes)
        semantic_results["summary"]["price_increases"] = sum(
            1 for c in price_changes if c["difference"] > 0
        )
        semantic_results["summary"]["price_decreases"] = sum(
            1 for c in price_changes if c["difference"] < 0
        )

        if price_changes:
            avg_change = sum(c["difference"] for c in price_changes) / len(price_changes)
            semantic_results["summary"]["average_price_change"] = round(avg_change, 2)

        if self.debug:
            print(f"\n✔ COMPLETED PRICE COMPARISON — {len(price_changes)} price changes detected.")
            print("=" * 120 + "\n")

        return semantic_results

    # ===============================================================
    # NEW: FLAT PRICE MATCHING (NO TABLE ALIGNMENT)
    # ===============================================================
    def _compare_all_prices_flat(
        self,
        old_tables: List[Dict[str, Any]],
        new_tables: List[Dict[str, Any]],
        parser,
    ) -> List[Dict[str, Any]]:
        """
        New strategy:
        1. Flatten ALL prices from ALL pricing tables in OLD and NEW.
        2. Build a signature for each price cell:
           (item_number, normalised_column_label)
        3. Match old vs new purely on this signature, ignoring table index/layout.
        4. For each matched pair with different price, emit a change record.

        This avoids:
        - Header similarity thresholds
        - Positional table matching
        - Missed changes when tables move around
        """

        if self.debug:
            print("\n" + "-" * 120)
            print("🔍 PRICE COMPARISON — FLAT SIGNATURE-BASED MATCHING")
            print("-" * 120)

        # Helper: flatten prices from tables
        def flatten_prices(
            tables: List[Dict[str, Any]],
        ) -> Tuple[List[Dict[str, Any]], Dict[Tuple[str, str], List[Dict[str, Any]]]]:
            flat: List[Dict[str, Any]] = []
            by_sig: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}

            for t_idx, table in enumerate(tables):
                is_pricing, confidence = parser._is_pricing_table(table)
                if not is_pricing:
                    continue

                data = table.get("data", [])
                if not data or len(data) < 2:
                    continue

                headers = [str(h).strip().lower() for h in data[0]]

                # Use robust parser's per-cell extraction
                extracted = parser._extract_prices_from_table(table)

                for p in extracted:
                    item_number = p.get("item_number")
                    if not item_number:
                        continue

                    col_index = p.get("col_index", 0)
                    if 0 <= col_index < len(headers):
                        column_label = headers[col_index]
                    else:
                        column_label = f"col_{col_index}"

                    # Normalise column label aggressively
                    norm_label = column_label.lower()
                    norm_label = norm_label.replace("  ", " ").strip()

                    sig = (item_number, norm_label)

                    # Enrich record with table+header info
                    enriched = dict(p)
                    enriched["table_index"] = table.get("index", t_idx)
                    enriched["column_label"] = norm_label

                    flat.append(enriched)
                    by_sig.setdefault(sig, []).append(enriched)

            return flat, by_sig

        # Flatten OLD and NEW
        old_flat, old_by_sig = flatten_prices(old_tables)
        new_flat, new_by_sig = flatten_prices(new_tables)

        if self.debug:
            print(f"\n📊 FLATTENED PRICE UNIVERSE")
            print(f"  OLD: {len(old_flat)} price cells across {len(old_by_sig)} signatures")
            print(f"  NEW: {len(new_flat)} price cells across {len(new_by_sig)} signatures")

        # Iterate over signatures present in BOTH versions
        changes: List[Dict[str, Any]] = []

        for sig, old_list in old_by_sig.items():
            if sig not in new_by_sig:
                # Signature exists only in OLD — could be a deletion, but we only
                # care about actual price differences where both sides exist.
                continue

            new_list = new_by_sig[sig]

            # Pair up entries. In practice, there is usually only one per signature;
            # if there are multiples, we zip them in order of (page, table, row).
            old_sorted = sorted(
                old_list,
                key=lambda x: (
                    x.get("page", 0),
                    x.get("table_index", 0),
                    x.get("row_index", 0),
                    x.get("col_index", 0),
                ),
            )
            new_sorted = sorted(
                new_list,
                key=lambda x: (
                    x.get("page", 0),
                    x.get("table_index", 0),
                    x.get("row_index", 0),
                    x.get("col_index", 0),
                ),
            )

            for old_p, new_p in zip(old_sorted, new_sorted):
                old_price = old_p.get("price")
                new_price = new_p.get("price")

                # Only flag if both sides have a usable price and they differ
                if old_price is None or new_price is None:
                    continue
                if old_price == new_price:
                    continue

                difference = new_price - old_price
                percent_change = (difference / old_price) * 100 if old_price > 0 else 0.0

                item_number, norm_label = sig

                change = {
                    "item_number": item_number,
                    "item_description": new_p.get("item_description") or old_p.get("item_description"),
                    "column_label": norm_label,
                    "old_price": old_price,
                    "new_price": new_price,
                    "difference": difference,
                    "percent_change": percent_change,
                    "old_location": {
                        "table": old_p.get("table_index"),
                        "row": old_p.get("row_index"),
                        "col": old_p.get("col_index"),
                        "page": old_p.get("page", 0),
                    },
                    "new_location": {
                        "table": new_p.get("table_index"),
                        "row": new_p.get("row_index"),
                        "col": new_p.get("col_index"),
                        "page": new_p.get("page", 0),
                    },
                    "old_raw_text": old_p.get("old_raw_text") or old_p.get("raw_text"),
                    "new_raw_text": new_p.get("new_raw_text") or new_p.get("raw_text"),
                }

                changes.append(change)

        if self.debug:
            print(f"\n📊 PRICE CHANGES DETECTED (before dedup): {len(changes)}")

        # Deduplicate by (item_number, column_label, new_location)
        seen = set()
        unique: List[Dict[str, Any]] = []

        for c in changes:
            item = c.get("item_number")
            col_label = c.get("column_label")
            loc = c.get("new_location", {})
            key = (item, col_label, loc.get("table"), loc.get("row"), loc.get("col"))

            if key not in seen:
                seen.add(key)
                unique.append(c)

        if self.debug:
            print(f"📊 PRICE CHANGES AFTER DEDUP: {len(unique)}")

        return unique

    # ===============================================================
    # PRICE SUMMARY
    # ===============================================================
    def _summarize_price_changes(self, price_changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create summary statistics for price changes.
        """
        if not price_changes:
            return {
                "total_changes": 0,
                "increases": 0,
                "decreases": 0,
                "average_change": 0,
                "largest_increase": 0,
                "largest_decrease": 0,
                "total_increase_amount": 0,
                "total_decrease_amount": 0,
            }

        increases = [c for c in price_changes if c["difference"] > 0]
        decreases = [c for c in price_changes if c["difference"] < 0]

        return {
            "total_changes": len(price_changes),
            "increases": len(increases),
            "decreases": len(decreases),
            "average_change": round(
                sum(c["difference"] for c in price_changes) / len(price_changes), 2
            ),
            "largest_increase": max((c["difference"] for c in increases), default=0),
            "largest_decrease": min((c["difference"] for c in decreases), default=0),
            "total_increase_amount": round(sum(c["difference"] for c in increases), 2),
            "total_decrease_amount": round(sum(c["difference"] for c in decreases), 2),
        }

    # ===============================================================
    # SEMANTIC (NON-PRICE) COMPARISON — UNCHANGED
    # ===============================================================
    def _compare_semantic(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        result = {
            "business_rule_changes": self._compare_rules(
                old.get("business_rules", {}), new.get("business_rules", {})
            ),
            "guidance_changes": self._compare_guidance(
                old.get("guidance", {}), new.get("guidance", {})
            ),
            "structural_changes": self._compare_structure(
                old.get("raw_paragraphs", []), new.get("raw_paragraphs", [])
            ),
            "table_changes": self._compare_tables(
                old.get("raw_tables", []), new.get("raw_tables", [])
            ),
            "summary": {},
        }
        result["summary"] = self._generate_summary(result)
        return result

    # RULES
    def _compare_rules(self, old_rules: Dict, new_rules: Dict) -> List[Dict[str, Any]]:
        changes = []
        old_list = self._flatten_rules(old_rules)
        new_list = self._flatten_rules(new_rules)

        for old in old_list:
            best = self._find_best_match(old, new_list)
            if best:
                sim = fuzz.ratio(old["text"], best["text"])
                if sim < 100:
                    changes.append(
                        {
                            "type": "modified",
                            "old_rule": old,
                            "new_rule": best,
                            "similarity": sim,
                        }
                    )
            else:
                changes.append({"type": "removed", "rule": old})

        for new in new_list:
            if not self._find_best_match(new, old_list):
                changes.append({"type": "added", "rule": new})

        return changes

    # GUIDANCE
    def _compare_guidance(self, old: Dict, new: Dict) -> List[Dict[str, Any]]:
        changes = []
        old_list = self._flatten_guidance(old)
        new_list = self._flatten_guidance(new)

        for old_item in old_list:
            best = self._find_best_match(old_item, new_list)
            if best:
                sim = fuzz.ratio(old_item["text"], best["text"])
                if sim < 100:
                    changes.append(
                        {
                            "type": "modified",
                            "old_guidance": old_item,
                            "new_guidance": best,
                            "similarity": sim,
                        }
                    )
            else:
                changes.append({"type": "removed", "guidance": old_item})

        for new_item in new_list:
            if not self._find_best_match(new_item, old_list):
                changes.append({"type": "added", "guidance": new_item})

        return changes

    # STRUCTURE
    def _compare_structure(
        self, old_paras: List[Dict], new_paras: List[Dict]
    ) -> Dict[str, List]:
        old_heads = [p for p in old_paras if p.get("is_heading")]
        new_heads = [p for p in new_paras if p.get("is_heading")]

        added, removed, modified = [], [], []

        for old in old_heads:
            best = self._find_best_match(old, new_heads)
            if best:
                sim = fuzz.ratio(old["text"], best["text"])
                if sim < 100:
                    modified.append(
                        {"old_section": old, "new_section": best, "similarity": sim}
                    )
            else:
                removed.append(old)

        for new in new_heads:
            if not self._find_best_match(new, old_heads):
                added.append(new)

        return {
            "sections_added": added,
            "sections_removed": removed,
            "sections_modified": modified,
        }

    # TABLE STRUCTURE
    def _compare_tables(
        self, old_tables: List[Dict], new_tables: List[Dict]
    ) -> Dict[str, List]:
        added: List[int] = []
        removed: List[int] = []
        modified: List[Dict[str, Any]] = []

        max_len = min(len(old_tables), len(new_tables))

        for i in range(max_len):
            old = old_tables[i]
            new = new_tables[i]

            old_r = len(old.get("data", []))
            new_r = len(new.get("data", []))
            old_c = len(old.get("data", [[]])[0]) if old.get("data") else 0
            new_c = len(new.get("data", [[]])[0]) if new.get("data") else 0

            if old_r != new_r or old_c != new_c:
                modified.append(
                    {
                        "table_index": i,
                        "old_dimensions": (old_r, old_c),
                        "new_dimensions": (new_r, new_c),
                    }
                )

        if len(new_tables) > len(old_tables):
            added = list(range(len(old_tables), len(new_tables)))
        elif len(old_tables) > len(new_tables):
            removed = list(range(len(new_tables), len(old_tables)))

        return {
            "tables_added": added,
            "tables_removed": removed,
            "tables_modified": modified,
        }

    # FLATTEN RULES
    def _flatten_rules(self, rules: Dict) -> List[Dict[str, Any]]:
        flat: List[Dict[str, Any]] = []
        for cat, rule_list in rules.items():
            if isinstance(rule_list, list):
                for rule in rule_list:
                    if isinstance(rule, dict):
                        flat.append(
                            {
                                "category": cat,
                                "text": rule.get("text", str(rule)),
                                "original": rule,
                            }
                        )
                    else:
                        flat.append(
                            {"category": cat, "text": str(rule), "original": rule}
                        )
        return flat

    # FLATTEN GUIDANCE
    def _flatten_guidance(self, gd: Dict) -> List[Dict[str, Any]]:
        flat: List[Dict[str, Any]] = []
        for section, content in gd.items():
            if isinstance(content, list):
                for item in content:
                    flat.append(
                        {"section": section, "text": str(item), "original": item}
                    )
            else:
                flat.append(
                    {"section": section, "text": str(content), "original": content}
                )
        return flat

    # BEST MATCH
    def _find_best_match(
        self, item: Dict[str, Any], candidates: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        best = None
        best_score = 0
        text = item.get("text", "")

        for cand in candidates:
            score = fuzz.ratio(text, cand.get("text", ""))
            if score > best_score and score >= self.similarity_threshold:
                best_score = score
                best = cand

        return best

    # SUMMARY
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        summary = {
            "total_rule_changes": len(results["business_rule_changes"]),
            "total_guidance_changes": len(results["guidance_changes"]),
            "sections_added": len(results["structural_changes"]["sections_added"]),
            "sections_removed": len(results["structural_changes"]["sections_removed"]),
            "sections_modified": len(
                results["structural_changes"]["sections_modified"]
            ),
            "tables_added": len(results["table_changes"]["tables_added"]),
            "tables_removed": len(results["table_changes"]["tables_removed"]),
            "tables_modified": len(results["table_changes"]["tables_modified"]),
        }

        rc = results["business_rule_changes"]
        summary["rules_added"] = sum(1 for r in rc if r["type"] == "added")
        summary["rules_removed"] = sum(1 for r in rc if r["type"] == "removed")
        summary["rules_modified"] = sum(1 for r in rc if r["type"] == "modified")

        gc = results["guidance_changes"]
        summary["guidance_added"] = sum(1 for g in gc if g["type"] == "added")
        summary["guidance_removed"] = sum(1 for g in gc if g["type"] == "removed")
        summary["guidance_modified"] = sum(1 for g in gc if g["type"] == "modified")

        return summary

    # FORMATTING
    def format_price_change(self, change: Dict[str, Any]) -> str:
        item = change.get("item_number", "Unknown")
        desc = change.get("item_description", "")
        old = change["old_price"]
        new = change["new_price"]
        diff = change["difference"]
        pct = change["percent_change"]

        diff_str = f"+${diff:.2f}" if diff > 0 else f"-${abs(diff):.2f}"
        pct_str = f"+{pct:.1f}%" if pct > 0 else f"{pct:.1f}%"

        label = f"Item {item}"
        if desc:
            label += (
                f" ({desc[:50]}...)" if len(desc) > 50 else f" ({desc})"
            )

        col_label = change.get("column_label")
        if col_label:
            label += f" [{col_label}]"

        return f"{label}: ${old:.2f} → ${new:.2f} ({diff_str}, {pct_str})"

    # EXPORT
    def export_results(self, results: Dict[str, Any], output_path: str):
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
