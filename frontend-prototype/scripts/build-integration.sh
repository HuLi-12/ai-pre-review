#!/usr/bin/env bash
# Build React app and integrate into FastAPI
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROTOTYPE_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$PROTOTYPE_DIR")"

echo "Building React app..."
cd "$PROTOTYPE_DIR"
npm run build

echo "Copying assets to static/prototype/"
mkdir -p "$ROOT_DIR/static/prototype"
cp -r dist/assets/* "$ROOT_DIR/static/prototype/"

echo "Generating Jinja2 template..."
cat > "$ROOT_DIR/templates/prototype.html" << 'TEMPLATE'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI Review Cockpit — Prototype</title>
    {% set assets_dir = "/static/prototype" %}
    {% set files = {
        "css": "index-{{ css_hash }}.css",
        "js": "index-{{ js_hash }}.js"
    } %}
    <link rel="stylesheet" href="{{ assets_dir }}/index-{{ css_hash }}.css">
  </head>
  <body>
    <div id="root"></div>
    <script src="{{ assets_dir }}/index-{{ js_hash }}.js"></script>
  </body>
</html>
TEMPLATE

# Get actual hashed filenames
CSS_FILE=$(ls dist/assets/index-*.css | xargs -n1 basename)
JS_FILE=$(ls dist/assets/index-*.js | xargs -n1 basename)
CSS_HASH=$(echo "$CSS_FILE" | sed 's/index-\(.*\)\.css/\1/')
JS_HASH=$(echo "$JS_FILE" | sed 's/index-\(.*\)\.js/\1/')

# Generate actual template with correct hashes
cat > "$ROOT_DIR/templates/prototype.html" << TEMPLATE
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI Review Cockpit — Prototype</title>
    <link rel="stylesheet" href="/static/prototype/${CSS_FILE}">
  </head>
  <body>
    <div id="root"></div>
    <script src="/static/prototype/${JS_FILE}"></script>
  </body>
</html>
TEMPLATE

echo "Done! Template created at templates/prototype.html"
echo "CSS: ${CSS_FILE}"
echo "JS:  ${JS_FILE}"
