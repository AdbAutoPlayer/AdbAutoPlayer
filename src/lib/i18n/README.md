# Translation Guidelines

## 🔥 IMPORTANT: Do NOT Replace Special Codes

When translating text in this project, **never replace or modify values wrapped in double curly braces** like `{{game}}`, `{{user}}`, `{{count}}`, etc.

### What are Special Codes?

These `{{...}}` patterns are **special codes** that automatically get filled in with real information (like a user's name or game title). They are NOT part of the text you should translate.

### ✅ Correct Translation Example
**Correct Translation (Japanese):**
```json
{
  "{{game}} Settings": "{{game}}設定"
}
```

### ❌ Incorrect Translation Example

**WRONG - Don't do this:**
```json
{
  "{{game}} Settings": "ゲーム設定"
}
```

The `{{game}}` placeholder was removed, which will break the translation.

### Key Rules for Translators

1. **Keep all `{{...}}` placeholders exactly as they are**
2. **Only translate the actual text around the placeholders**
3. **Maintain the same placeholder positioning** (you can move them within the sentence if needed for grammar)
4. **Never translate the content inside the curly braces**

### More Complex Example

**Original:**
```json
{
  "Welcome {{user}}, you have {{count}} new messages": "Welcome {{user}}, you have {{count}} new messages"
}
```

**Correct Japanese Translation:**
```json
{
  "Welcome {{user}}, you have {{count}} new messages": "{{user}}さん、{{count}}件の新しいメッセージがあります"
}
```

Notice how the placeholders `{{user}}` and `{{count}}` are preserved but moved to fit Japanese grammar structure.

## 📚 Learn More

For more information about ICU Message Format and placeholder syntax, check out the official documentation:
- [ICU Message Format Documentation](https://unicode-org.github.io/icu/userguide/format_parse/messages/)
- [Format.JS ICU Syntax Guide](https://formatjs.github.io/docs/core-concepts/icu-syntax/)
