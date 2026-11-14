import { createCn } from "cn/config";

// Teach the merger our @theme font-size tokens (style.css --text-*). Unknown
// `text-*` values are otherwise treated as colours, so `cn("text-caption",
// "text-muted-foreground")` silently dropped the size.
export const cn = createCn({
  extend: {
    classGroups: {
      "font-size": [{ text: ["caption", "small", "body", "body-large", "title-small", "title-medium", "title-large", "page-title", "display"] }],
    },
  },
});
