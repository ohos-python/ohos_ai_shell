import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parent


def load_json(path):
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(), object_pairs_hook=reject_duplicates)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_path(root, relative):
    path = root / relative
    require(not path.is_symlink(), f"Symlink is not allowed: {relative}")
    resolved = path.resolve()
    require(resolved.is_relative_to(root.resolve()), f"Path escapes bundle: {relative}")
    require(resolved.relative_to(root.resolve()).as_posix() == relative, f"Noncanonical path: {relative}")
    require(resolved.is_file(), f"Missing file: {relative}")
    return resolved


def check_parameter_schema(value):
    if isinstance(value, dict):
        require(not any(key in value for key in ("$ref", "$dynamicRef", "$id")), "Parameter schemas must be self-contained")
        for child in value.values():
            check_parameter_schema(child)
    elif isinstance(value, list):
        for child in value:
            check_parameter_schema(child)


def validate_bundle(bundle_root):
    schemas = {name: load_json(ROOT / "schemas" / f"{name}.schema.json") for name in ("common", "bundle", "evidence", "recipe")}
    registry = Registry()
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))

    def validate_record(kind, record):
        Draft202012Validator(schemas[kind], registry=registry, format_checker=FormatChecker()).validate(record)

    manifest = load_json(bundle_root / "manifest.json")
    validate_record("bundle", manifest)
    require(manifest["status"] == "draft", "Example validator does not authorize release manifests")
    files = {}
    for item in manifest["files"]:
        require(item["path"] not in files, "Duplicate file path")
        data = local_path(bundle_root, item["path"]).read_bytes()
        require(len(data) == item["bytes"], f"File size mismatch: {item['path']}")
        require(hashlib.sha256(data).hexdigest() == item["sha256"], f"File digest mismatch: {item['path']}")
        files[item["path"]] = item
    records = {}
    entry_paths = set()
    for entry in manifest["entries"]:
        require(entry["path"] in files, "Entry is missing from file manifest")
        require(entry["path"] not in entry_paths, "Duplicate entry path")
        entry_paths.add(entry["path"])
        record = load_json(local_path(bundle_root, entry["path"]))
        require(record["kind"] == entry["kind"], "Entry kind mismatch")
        require((record["id"], record["revision"]) == (entry["id"], entry["revision"]), "Entry identity mismatch")
        validate_record(entry["kind"].lower(), record)
        key = (record["kind"], record["id"], record["revision"])
        require(key not in records, "Duplicate record identity")
        records[key] = record
    for index in manifest["indexes"]:
        require(index["path"] in files, "Index is missing from manifest")
        require(index["corpus_revision"] == manifest["revision"], "Index corpus revision mismatch")

    for record in records.values():
        if record["kind"] == "Evidence":
            require(record["visibility"]["scope"] == "public", "Shared bundles must not contain session-private evidence")
            source = record["source"]
            require(source["snapshot_path"] in files, "Source snapshot missing from manifest")
            require(source["sha256"] == files[source["snapshot_path"]]["sha256"], "Source digest mismatch")
            continue
        for reference in record["evidence_refs"]:
            require(("Evidence", reference["id"], reference["revision"]) in records, "Unknown evidence reference")
        for reference in record["dependencies"]:
            require(("Recipe", reference["id"], reference["revision"]) in records, "Unknown recipe dependency")
        for test in record["test_records"]:
            reference = test["evidence_ref"]
            evidence = records.get(("Evidence", reference["id"], reference["revision"]))
            require(evidence is not None and evidence["evidence_type"] == "test_report", "Test must reference test_report evidence")
        parameter_schema = record["parameter_schema"]
        check_parameter_schema(parameter_schema)
        Draft202012Validator.check_schema(parameter_schema)
        parameters = parameter_schema["properties"]
        artifacts = {item["id"] for item in record["artifacts"]}
        require(len(artifacts) == len(record["artifacts"]), "Duplicate artifact identity")
        previous_steps = set()
        for step in record["steps"]:
            require(step["step_id"] not in previous_steps, "Duplicate step identity")
            require(set(step["depends_on"]).issubset(previous_steps), "Steps must use preceding dependencies only")
            previous_steps.add(step["step_id"])
            require(set(step["artifact_refs"]).issubset(artifacts), "Unknown artifact reference")
            for binding in step["arguments"].values():
                if "parameter" in binding:
                    require(binding["parameter"] in parameters, "Unknown step parameter")
        for check in record["verification"]:
            binding = check["expected"]
            if "parameter" in binding:
                require(binding["parameter"] in parameters, "Unknown verification parameter")

    def visit(key, visiting, completed):
        require(key not in visiting, "Recipe dependency cycle")
        if key in completed:
            return
        visiting.add(key)
        for reference in records[key]["dependencies"]:
            visit(("Recipe", reference["id"], reference["revision"]), visiting, completed)
        visiting.remove(key)
        completed.add(key)

    completed = set()
    for key in records:
        if key[0] == "Recipe":
            visit(key, set(), completed)
    return {"schemas": len(schemas), "files": len(files), "records": len(records), "release_authorized": False}


if __name__ == "__main__":
    print(json.dumps(validate_bundle(ROOT / "examples"), ensure_ascii=False, indent=2))
