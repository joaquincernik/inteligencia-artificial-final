#!/usr/bin/env python3
"""
Script para filtrar técnicas de MITRE ATT&CK que han sido retiradas de la matriz.

Toma el fichero JSON de MITRE ATT&CK Enterprise y:
1. Extrae las técnicas y marca aquellas que están deprecadas/revocadas
2. Filtra una lista de IDs solicitados
3. Opcionalmente, genera un JSON con solo las técnicas vigentes

Uso:
    python filter_mitre_techniques.py --json data/mitre/enterprise-attack.json
    python filter_mitre_techniques.py --json data/mitre/enterprise-attack.json --techs T1062 T1108 T1131
    python filter_mitre_techniques.py --json data/mitre/enterprise-attack.json --output techniques_vigentes.json
"""

import argparse
import json
import sys


def get_valid_technique_ids(mitre_json_path):
    """Extrae las técnicas del matrix de MITRE y marca las deprecadas/revocadas."""
    with open(mitre_json_path, encoding="utf-8") as f:
        data = json.load(f)

    objects = data.get("objects", [])
    techniques = [obj for obj in objects if obj.get("type") == "attack-pattern"]

    results = []
    for obj in techniques:
        external_id = None
        is_deprecated = False

        # Buscar el ID de técnica en external_references
        for ref in obj.get("external_references", []):
            if ref.get("source_name") == "mitre-attack":
                external_id = ref.get("external_id")
                # Verificar revoked tanto en el ref como en el objeto
                if ref.get("revoked") or obj.get("revoked"):
                    is_deprecated = True
                # También revisar x_mitre_deprecated del objeto
                if obj.get("x_mitre_deprecated"):
                    is_deprecated = True
                break

        if not external_id:
            continue

        results.append({
            "id": external_id,
            "name": obj.get("name", ""),
            "deprecated": is_deprecated,
            "tactics": [
                p.get("phase_name", "").replace("-", " ").strip().title()
                for p in obj.get("kill_chain_phases", [])
            ],
            "description": (obj.get("description") or "")[:1200],
        })

    return results


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Filtrar técnicas de MITRE ATT&CK deprecadas y revocadas"
    )
    parser.add_argument("--json", required=True, help="Ruta al enterprise-attack.json")
    parser.add_argument("--techs", nargs="+", help="IDs de técnicas a consultar")
    parser.add_argument("--output", help="Ruta JSON de salida (solo técnicas vigentes)")

    args = parser.parse_args(argv)

    valid_data = get_valid_technique_ids(args.json)
    active = sum(1 for v in valid_data if not v["deprecated"])
    deprecated = sum(1 for v in valid_data if v["deprecated"])

    print(f"Matrix MITRE ATT&CK: {len(valid_data)} técnicas")
    print(f"  Vigentes: {active}  |  Deprecadas/revocadas: {deprecated}")

    if args.techs:
        requested = [v for v in valid_data if v["id"] in args.techs]
        print(f"\nTécnicas solicitadas: {args.techs}")
        for t in requested:
            status = "DEPRECATED/REVOKED" if t["deprecated"] else "ACTIVO"
            print(f"  {t['id']}: {status} - {t['name'][:50]}")
        removed = set(args.techs) - {t["id"] for t in requested}
        if removed:
            print(f"  No encontradas en el matrix actual: {sorted(removed)}")

    if args.output:
        # Generar JSON con solo técnicas vigentes (no deprecated/revoked)
        filtered = {v["id"]: v for v in valid_data if not v["deprecated"]}
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False, indent=2)
        print(f"\nJSON filtrado guardado: {args.output} ({len(filtered)} técnicas vigentes)")


if __name__ == "__main__":
    main()
