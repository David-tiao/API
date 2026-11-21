const fs = require('fs');
const parser = require('@babel/parser');

const filename = process.argv[2];
if (!filename) {
  process.stderr.write('usage: node js_ast_analyzer.cjs <file.js>\n');
  process.exit(2);
}

const source = fs.readFileSync(filename, 'utf8');
const result = { endpoints: [], chunks: [] };
const seen = new Set();

function propertyName(node) {
  if (!node) return null;
  if (node.type === 'Identifier') return node.name;
  if (node.type === 'StringLiteral' || node.type === 'NumericLiteral') return String(node.value);
  return null;
}

function staticString(node) {
  if (!node) return null;
  if (node.type === 'StringLiteral') return node.value;
  if (node.type === 'TemplateLiteral') {
    let value = '';
    for (let i = 0; i < node.quasis.length; i++) {
      value += node.quasis[i].value.cooked ?? node.quasis[i].value.raw;
      if (i < node.expressions.length) value += '{id}';
    }
    return value;
  }
  if (node.type === 'BinaryExpression' && node.operator === '+') {
    const left = staticString(node.left);
    const right = staticString(node.right);
    if (left !== null && right !== null) return left + right;
    if (left !== null) return left + '{id}';
    if (right !== null) return right.startsWith('/') ? right : '{id}' + right;
  }
  return null;
}

function objectProperty(node, key) {
  if (!node || node.type !== 'ObjectExpression') return null;
  for (const prop of node.properties || []) {
    if (prop.type !== 'ObjectProperty' && prop.type !== 'ObjectMethod') continue;
    if (propertyName(prop.key) === key) return prop.value || null;
  }
  return null;
}

function objectKeys(node) {
  if (node && node.type === 'CallExpression' && node.callee && node.callee.type === 'MemberExpression' && propertyName(node.callee.property) === 'stringify') {
    return objectKeys(node.arguments && node.arguments[0]);
  }
  if (!node || node.type !== 'ObjectExpression') return [];
  return (node.properties || [])
    .filter(p => p.type === 'ObjectProperty' || p.type === 'ObjectMethod')
    .map(p => propertyName(p.key))
    .filter(Boolean);
}

function getMethod(node, fallback) {
  const methodNode = objectProperty(node, 'method');
  const method = staticString(methodNode);
  return (method || fallback || 'GET').toUpperCase();
}

function pushEndpoint(method, urlNode, configNode, loc, kind, bodyNode = null) {
  const url = staticString(urlNode);
  if (!url || !url.trim()) return;
  if (/^(data:|blob:|javascript:|mailto:)/i.test(url)) return;
  const paramsNode = objectProperty(configNode, 'params');
  const dataNode = bodyNode || objectProperty(configNode, 'data') || objectProperty(configNode, 'body');
  const key = [method, url, loc && loc.start && loc.start.line].join('|');
  if (seen.has(key)) return;
  seen.add(key);
  result.endpoints.push({
    method: method.toUpperCase(),
    url,
    kind,
    line: loc && loc.start ? loc.start.line : null,
    column: loc && loc.start ? loc.start.column : null,
    query_fields: objectKeys(paramsNode),
    body_fields: objectKeys(dataNode),
  });
}

function memberInfo(node) {
  if (!node || node.type !== 'MemberExpression') return null;
  const prop = node.computed ? staticString(node.property) : propertyName(node.property);
  const object = node.object && node.object.type === 'Identifier' ? node.object.name : null;
  return { object, prop };
}

function walk(node) {
  if (!node || typeof node !== 'object') return;
  if (Array.isArray(node)) {
    for (const item of node) walk(item);
    return;
  }

  if (node.type === 'ImportExpression') {
    const chunk = staticString(node.source);
    if (chunk) result.chunks.push(chunk);
  }

  if (node.type === 'CallExpression') {
    const callee = node.callee;
    if (callee && callee.type === 'Import') {
      const chunk = staticString(node.arguments && node.arguments[0]);
      if (chunk) result.chunks.push(chunk);
    } else if (callee && callee.type === 'Identifier' && callee.name === 'fetch') {
      const init = node.arguments && node.arguments[1];
      pushEndpoint(getMethod(init, 'GET'), node.arguments && node.arguments[0], init, node, 'fetch');
    } else if (callee && callee.type === 'MemberExpression') {
      const info = memberInfo(callee);
      if (info && ['get', 'post', 'put', 'patch', 'delete', 'head', 'options'].includes(String(info.prop).toLowerCase())) {
        const method = String(info.prop).toUpperCase();
        const urlNode = node.arguments && node.arguments[0];
        const configNode = ['GET', 'HEAD', 'DELETE', 'OPTIONS'].includes(method)
          ? (node.arguments && node.arguments[1]) : (node.arguments && node.arguments[2]);
        const bodyNode = ['GET', 'HEAD', 'DELETE', 'OPTIONS'].includes(method) ? null : (node.arguments && node.arguments[1]);
        pushEndpoint(method, urlNode, configNode, node, 'axios_or_http_client', bodyNode);
      } else if (info && String(info.prop).toLowerCase() === 'request') {
        const config = node.arguments && node.arguments[0];
        pushEndpoint(getMethod(config, 'GET'), objectProperty(config, 'url'), config, node, 'request_config');
      } else if (info && String(info.prop).toLowerCase() === 'open') {
        const method = staticString(node.arguments && node.arguments[0]) || 'GET';
        pushEndpoint(method, node.arguments && node.arguments[1], null, node, 'xhr_open');
      }
    } else if (callee && callee.type === 'Identifier' && callee.name === 'request') {
      const config = node.arguments && node.arguments[0];
      pushEndpoint(getMethod(config, 'GET'), objectProperty(config, 'url'), config, node, 'request_config');
    }
  }

  for (const key of Object.keys(node)) {
    if (['loc', 'start', 'end', 'extra', 'comments', 'tokens'].includes(key)) continue;
    walk(node[key]);
  }
}

try {
  const ast = parser.parse(source, {
    sourceType: 'unambiguous',
    errorRecovery: true,
    plugins: ['jsx', 'typescript', 'decorators-legacy', 'dynamicImport', 'optionalChaining', 'classProperties', 'topLevelAwait'],
  });
  walk(ast);
} catch (error) {
  process.stderr.write(`AST_PARSE_ERROR: ${error.message}\n`);
}

result.chunks = [...new Set(result.chunks)];
process.stdout.write(JSON.stringify(result));
