const fs = require('node:fs');

// Fix 1: schemas/page.tsx - remove unused apiGet import
{
  const fp = 'app/seo/schemas/page.tsx';
  let content = fs.readFileSync(fp, 'utf8');
  content = content.replace('import { _apiGet, apiSend', 'import { apiSend');
  fs.writeFileSync(fp, content);
  console.log('Fixed schemas/page.tsx - removed _apiGet import');
}

// Fix 2: studio/page.tsx - remove unused useMemo import
{
  const fp = 'app/studio/page.tsx';
  let content = fs.readFileSync(fp, 'utf8');
  content = content.replace(', _useMemo,', ',');
  content = content.replace('{ _useMemo, ', '{ ');
  content = content.replace('{ useEffect, _useMemo, ', '{ useEffect, ');
  content = content.replace(', _useMemo }', ' }');
  fs.writeFileSync(fp, content);
  console.log('Fixed studio/page.tsx - removed _useMemo import');
}

// Fix 3: editor/page.tsx - use aliased destructuring for typed props
{
  const fp = 'app/studio/editor/page.tsx';
  let content = fs.readFileSync(fp, 'utf8');

  // These props are destructured from typed interfaces - use aliased destructuring
  // { _captions } -> { captions: _captions }
  const aliases = [
    ['_captions', 'captions'],
    ['_setUgcStyleCategoryId', 'setUgcStyleCategoryId'],
    ['_setUgcPreviewTemplateId', 'setUgcPreviewTemplateId'],
    ['_subtitles', 'subtitles'],
    ['_selectedLibraryItem', 'selectedLibraryItem'],
    ['_publishCreative', 'publishCreative'],
    ['_setPublishMode', 'setPublishMode'],
    ['_videoCanvasAspectRatio', 'videoCanvasAspectRatio'],
    ['_visibleEditorLayers', 'visibleEditorLayers'],
    ['_applyLibraryItemToEditor', 'applyLibraryItemToEditor'],
  ];

  for (const [alias, original] of aliases) {
    // Replace { ..._alias... } with { ...original: _alias... } in destructuring
    const re = new RegExp(String.raw`\b${alias}\b(?!\s*:)`, 'g');
    content = content.replace(re, `${original}: ${alias}`);
  }

  fs.writeFileSync(fp, content);
  console.log('Fixed editor/page.tsx - aliased destructuring');
}

// Fix 4: workspace/page.tsx - use aliased destructuring
{
  const fp = 'app/studio/workspace/page.tsx';
  let content = fs.readFileSync(fp, 'utf8');
  content = content.replace(', _accounts,', ', accounts: _accounts,');
  fs.writeFileSync(fp, content);
  console.log('Fixed workspace/page.tsx - aliased accounts destructuring');
}

console.log('Done');
