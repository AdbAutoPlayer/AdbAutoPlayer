import { marked, type Tokens } from "marked";

const renderer = new marked.Renderer();

renderer.link = function ({ href, text }) {
  const target = "_blank";
  return `<a class="anchor" href="${href}" target="${target}" rel="noopener noreferrer">${text}</a>`;
};

renderer.heading = function ({ tokens, depth }: Tokens.Heading) {
  const sizes = [
    "text-2xl",
    "text-xl",
    "text-lg",
    "text-base",
    "text-sm",
    "text-xs",
  ];

  return `<h${depth} class="${sizes[depth - 1] || "text-base"} font-bold my-2">${this.parser.parseInline(tokens)}</h${depth}>\n`;
};

renderer.strong = function ({ tokens }: Tokens.Strong): string {
  return `<strong class="fond-bold">${this.parser.parseInline(tokens)}</strong>`;
};

renderer.image = function ({ href, title, text, tokens }) {
  // GitHub user attachments do not render.
  if (href.startsWith("https://github.com/user-attachments/")) {
    return ``;
  }

  return `<img src="${href}" alt="${text}" ${title ? `title="${title}"` : ""} />`;
};

renderer.em = function ({ tokens }: Tokens.Em) {
  return `<em class="italic">${renderer.parser.parseInline(tokens)}</em>`;
};

renderer.list = function (token: Tokens.List) {
  const ordered = token.ordered;
  const start = token.start;

  let body = "";
  for (let j = 0; j < token.items.length; j++) {
    const item = token.items[j];
    body += this.listitem(item);
  }

  const type = ordered ? "ol" : "ul";
  const startAttr = ordered && start !== 1 ? ' start="' + start + '"' : "";
  return "<" + type + startAttr + ">\n" + body + "</" + type + ">\n";
};

renderer.listitem = function (item: Tokens.ListItem) {
  let itemBody = "";
  if (item.task) {
    const checkbox = this.checkbox({ checked: !!item.checked });
    if (item.loose) {
      if (item.tokens[0]?.type === "paragraph") {
        item.tokens[0].text = checkbox + " " + item.tokens[0].text;
        if (
          item.tokens[0].tokens &&
          item.tokens[0].tokens.length > 0 &&
          item.tokens[0].tokens[0].type === "text"
        ) {
          item.tokens[0].tokens[0].text =
            checkbox + " " + encodeURI(item.tokens[0].tokens[0].text);
          item.tokens[0].tokens[0].escaped = true;
        }
      } else {
        item.tokens.unshift({
          type: "text",
          raw: checkbox + " ",
          text: checkbox + " ",
          escaped: true,
        });
      }
    } else {
      itemBody += checkbox + " ";
    }
  }

  itemBody += this.parser.parse(item.tokens, item.loose);
  return `<li>${itemBody}</li><br/>\n`;
};

renderer.text = function (token: Tokens.Text | Tokens.Escape): string {
  const processText = (text: string): string => {
    // Regex for @username (alphanumeric only, at least one char after @)
    const githubUserRegex = /@([a-zA-Z0-9]+)/g;

    // Replace @username with anchor tag
    return text.replace(githubUserRegex, (match, username) => {
      return `<a class="anchor" rel="noopener noreferrer" href="https://github.com/${username}" target="_blank">${match}</a>`;
    });
  };

  if ("tokens" in token && token.tokens) {
    // If token.tokens exist, parse inline as before
    const parsedInline = this.parser.parseInline(token.tokens);
    // Then process the result for @username patterns as well
    return processText(parsedInline);
  } else {
    // Just process the plain text token
    return processText(token.text);
  }
};

marked.setOptions({
  renderer,
  gfm: true,
  breaks: true,
});

export default marked;
