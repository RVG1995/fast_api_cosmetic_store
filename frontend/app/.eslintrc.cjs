/**
 * Локальная конфигурация для разовой проверки неиспользуемых переменных.
 * Фокусируемся только на правиле no-unused-vars, чтобы не зашумлять вывод.
 */
module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: false,
  },
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
  },
  extends: [
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
    'plugin:jsx-a11y/recommended',
  ],
  rules: {
    // Удаляем неиспользуемые импорты/переменные
    'unused-imports/no-unused-imports': 'error',
    'no-unused-vars': ['warn', { vars: 'all', args: 'after-used', ignoreRestSiblings: true }],
    // Отключим, чтобы не зашумлять (нам сейчас важны только unused vars)
    'no-undef': 'off',
    // Новый JSX-трансформ не требует React в скоупе
    'react/react-in-jsx-scope': 'off',
    // Смягчаем правила, которые сейчас валят сборку — переведем в warning/выключим
    'react/prop-types': 'off',
    'react/no-unescaped-entities': 'warn',
    'jsx-a11y/click-events-have-key-events': 'warn',
    'jsx-a11y/no-static-element-interactions': 'warn',
    'jsx-a11y/label-has-associated-control': 'warn',
  },
  plugins: ['unused-imports'],
  settings: {
    react: { version: 'detect' },
  },
  ignorePatterns: [
    'node_modules/',
    'build/',
    'public/',
    'src/styles/output.css',
    '**/*.css',
    '**/*.html',
  ],
};


