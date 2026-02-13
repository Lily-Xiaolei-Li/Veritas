declare module "micromark-extension-mark" {
  import type { Extension, HtmlExtension } from "micromark-util-types";
  
  export function pandocMark(): Extension;
  export const pandocMarkHtml: HtmlExtension;
}
