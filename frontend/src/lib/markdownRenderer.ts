import { marked } from "marked";

const renderer = new marked.Renderer();

renderer.link = function ({ href, text }) {
  const target = "_blank";
  return `<a class="anchor" href="${href}" target="${target}" rel="noopener noreferrer">${text}</a>`;
};

renderer.heading = function ({ text, depth }) {
  const sizes = [
    "text-2xl",
    "text-xl",
    "text-lg",
    "text-base",
    "text-sm",
    "text-xs",
  ];
  return `<h${depth} class="${sizes[depth - 1] || "text-base"} font-bold my-2">${text}</h${depth}>`;
};

renderer.strong = function ({ text }) {
  console.log(text);
  return `<strong class="font-bold">${text}</strong>`;
};

renderer.image = function ({ href, title, text, tokens }) {
  // GitHub user attachments do not render.
  if (href.startsWith("https://github.com/user-attachments/")) {
    return ``;
  }

  return `<img src="${href}" alt="${text}" ${title ? `title="${title}"` : ""} />`;
};

renderer.em = function ({ text }) {
  return `<em class="italic">${text}</em>`;
};

marked.setOptions({
  renderer,
});

export default marked;
