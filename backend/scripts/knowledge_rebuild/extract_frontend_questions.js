/**
 * 把前端静态题库 frontend/src/data/pythonTrialQuestions.ts 导出为 JSON。
 *
 * 该文件的 description 字段是 `wrapExploration(...)` 的调用结果，正则抠不出真实
 * 文案，所以这里用 typescript 把依赖链编译后真正执行一遍，取
 * PYTHON_TRIAL_QUESTIONS 的运行时值——拿到的就是学生实际看到的文本。
 *
 * 两个实现细节：
 * 1. frontend/package.json 声明了 "type": "module"，Node 会把编译产物当 ESM，
 *    所以这里不用 module._compile，而是自己用 Function 包一层 CommonJS 作用域。
 * 2. 依赖链会牵出 src/api/*（axios、鉴权等运行时依赖），题目文本用不到，
 *    统一替换为空桩，避免为了取静态数据而拉起整个前端运行时。
 *
 * 用法：node extract_frontend_questions.js <输出JSON路径>
 */
const fs = require('fs');
const path = require('path');

const FRONTEND_ROOT = path.resolve(__dirname, '../../../frontend');
const SRC_ROOT = path.join(FRONTEND_ROOT, 'src');
const TS_ENTRY = path.join(SRC_ROOT, 'data/pythonTrialQuestions.ts');
const ts = require(path.join(FRONTEND_ROOT, 'node_modules/typescript'));

const cache = new Map();

function resolveTs(request, fromFile) {
  const base = path.resolve(path.dirname(fromFile), request);
  for (const candidate of [base, `${base}.ts`, path.join(base, 'index.ts')]) {
    if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) return candidate;
  }
  return null;
}

/** 空桩：任何 API / 第三方模块都返回一个"取什么属性都得到空函数"的代理。 */
function stubModule() {
  return new Proxy(
    {},
    {
      get: (_target, prop) => {
        if (prop === '__esModule') return true;
        if (prop === 'default') return stubModule();
        return () => undefined;
      },
    },
  );
}

function loadTs(filename) {
  if (cache.has(filename)) return cache.get(filename).exports;

  const source = fs.readFileSync(filename, 'utf8');
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    },
    fileName: filename,
  });

  const module = { exports: {} };
  cache.set(filename, module);

  const localRequire = (request) => {
    // 相对导入：继续按 TS 加载；解析不到的（含 src/api/*、第三方包）走空桩
    if (request.startsWith('.')) {
      const resolved = resolveTs(request, filename);
      if (!resolved) return stubModule();
      if (resolved.includes(`${path.sep}api${path.sep}`)) return stubModule();
      return loadTs(resolved);
    }
    return stubModule();
  };

  const fn = new Function('exports', 'require', 'module', '__filename', '__dirname', outputText);
  fn(module.exports, localRequire, module, filename, path.dirname(filename));
  return module.exports;
}

const outPath = process.argv[2];
if (!outPath) {
  console.error('用法: node extract_frontend_questions.js <输出JSON路径>');
  process.exit(1);
}

const questions = loadTs(TS_ENTRY).PYTHON_TRIAL_QUESTIONS;
if (!Array.isArray(questions) || questions.length === 0) {
  console.error('未能从 pythonTrialQuestions.ts 读到 PYTHON_TRIAL_QUESTIONS');
  process.exit(2);
}

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(questions, null, 2), 'utf8');
console.log(`导出 ${questions.length} 道前端静态题 -> ${outPath}`);
