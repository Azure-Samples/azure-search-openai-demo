import { visit } from "unist-util-visit";

/* 
The code in this module is for supporting anchor links in the markdown viewer, see:
https://github.com/uiwjs/react-md-editor/issues/356
*/

const onNode = (node: any) => {
    if (node.tagName != "a" || typeof node.properties?.href !== "string") {
        return;
    }

    const url = node.properties.href;
    if (!url.startsWith("#")) return;

    node.properties.onClick = (e: any) => {
        e.preventDefault();

        // Scroll to anchor
        const hash = url.replace("#", "");
        const id = decodeURIComponent(hash);
        const element = document.getElementById(id);

        if (!element) return;
        element.scrollIntoView();
    };
};

export default function rehypeAnchorOnClick() {
    return (tree: any) => {
        visit(tree, "element", onNode);
    };
}
