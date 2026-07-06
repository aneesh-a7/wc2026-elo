"""Inject the freshly-built payload into the HTML template so the site is
self-contained (opens with no server, no fetch). Idempotent: replaces the
existing `const DATA = {...};` block each run."""
import json, re
from paths import PAYLOAD_JSON, INDEX_HTML

def build():
    payload = json.dumps(json.load(open(PAYLOAD_JSON)), ensure_ascii=False)
    html = INDEX_HTML.read_text()
    new = re.sub(r"const DATA = \{.*?\};\s*\n</script>",
                 "const DATA = " + payload + ";\n</script>",
                 html, count=1, flags=re.DOTALL)
    if new == html:
        raise SystemExit("ERROR: could not find `const DATA = {...};` block to replace.")
    INDEX_HTML.write_text(new)
    print(f"site/index.html rebuilt ({len(payload):,} bytes of data embedded)")

if __name__ == "__main__":
    build()
