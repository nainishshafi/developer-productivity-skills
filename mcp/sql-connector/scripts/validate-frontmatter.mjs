import fs from 'node:fs';
import path from 'node:path';
import YAML from 'yaml';

const rootDir = path.resolve(import.meta.dirname, '../../..'); // developer-productivity-skills root
console.log(`Scanning skills in ${rootDir}...`);

function getAllFiles(dir, filter) {
  if (!fs.existsSync(dir)) return [];
  let results = [];
  const list = fs.readdirSync(dir);
  for (const file of list) {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    if (stat.isDirectory()) {
      if (file !== 'node_modules' && file !== '.git') {
        results = results.concat(getAllFiles(fullPath, filter));
      }
    } else if (filter(fullPath)) {
      results.push(fullPath);
    }
  }
  return results;
}

const skillFiles = getAllFiles(path.join(rootDir, '.github', 'skills'), (p) => p.endsWith('SKILL.md'));
const agentFiles = getAllFiles(path.join(rootDir, '.github', 'agents'), (p) => p.endsWith('.md'));
const yamlFiles = getAllFiles(path.join(rootDir, '.github'), (p) => p.endsWith('.yaml') || p.endsWith('.yml'));

let errorsFound = 0;
let validCount = 0;

function validateFrontmatterList(label, files) {
  console.log(`\nValidating ${files.length} ${label}...\n`);
  for (const filePath of files) {
    const content = fs.readFileSync(filePath, 'utf8');
    const relPath = path.relative(rootDir, filePath);

    if (!content.startsWith('---')) {
      console.error(`❌ [${relPath}] Missing opening '---' frontmatter boundary`);
      errorsFound++;
      continue;
    }

    const secondSepIndex = content.indexOf('\n---', 3);
    if (secondSepIndex === -1) {
      console.error(`❌ [${relPath}] Missing closing '---' frontmatter boundary`);
      errorsFound++;
      continue;
    }

    const frontmatterStr = content.slice(3, secondSepIndex).trim();

    try {
      const parsed = YAML.parse(frontmatterStr);
      if (!parsed || typeof parsed !== 'object') {
        console.error(`❌ [${relPath}] Frontmatter parsed to non-object: ${typeof parsed}`);
        errorsFound++;
        continue;
      }
      if (!parsed.name) {
        console.error(`❌ [${relPath}] Missing required 'name' field`);
        errorsFound++;
        continue;
      }
      if (!parsed.description) {
        console.error(`❌ [${relPath}] Missing required 'description' field`);
        errorsFound++;
        continue;
      }
      console.log(`✅ [${relPath}] valid (name: ${parsed.name})`);
      validCount++;
    } catch (err) {
      console.error(`❌ [${relPath}] YAML parse error:\n   ${err.message}`);
      errorsFound++;
    }
  }
}

validateFrontmatterList('SKILL.md frontmatter files', skillFiles);
validateFrontmatterList('.github/agents/*.md frontmatter files', agentFiles);

console.log(`\nValidating ${yamlFiles.length} standalone YAML/YML files...\n`);
for (const filePath of yamlFiles) {
  const content = fs.readFileSync(filePath, 'utf8');
  const relPath = path.relative(rootDir, filePath);
  try {
    YAML.parse(content);
    console.log(`✅ [${relPath}] valid YAML`);
    validCount++;
  } catch (err) {
    console.error(`❌ [${relPath}] YAML parse error:\n   ${err.message}`);
    errorsFound++;
  }
}

console.log(`\n========================================`);
console.log(`Results: ${validCount} valid, ${errorsFound} errors`);
console.log(`========================================`);

if (errorsFound > 0) {
  process.exit(1);
}
