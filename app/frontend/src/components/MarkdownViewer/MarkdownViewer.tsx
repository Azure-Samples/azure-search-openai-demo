import React, { useState, useEffect } from "react";
import MarkdownPreview from "@uiw/react-markdown-preview";
import rehypeAnchorOnClick from "./AnchorLinksHandler";
import styles from "./MarkdownViewer.module.css";
import { Spinner, SpinnerSize, MessageBar, MessageBarType, Link, IconButton } from "@fluentui/react";

interface MarkdownViewerProps {
    src: string;
}

export const MarkdownViewer: React.FC<MarkdownViewerProps> = ({ src }) => {
    const [markdownContent, setMarkdownContent] = useState<string>("");
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        const fetchMarkdown = async () => {
            try {
                const response = await fetch(src);

                if (!response.ok) {
                    throw new Error("Failed loading markdown file.");
                }

                const markdownText = await response.text();
                setMarkdownContent(markdownText);
            } catch (error: any) {
                setError(error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchMarkdown();
    }, [src]);

    return (
        <div>
            {isLoading ? (
                <div className={`${styles.loading} ${styles.markdownViewer}`}>
                    <Spinner size={SpinnerSize.large} label="Loading file" />
                </div>
            ) : error ? (
                <div className={`${styles.error} ${styles.markdownViewer}`}>
                    <MessageBar messageBarType={MessageBarType.error} isMultiline={false}>
                        {error.message}
                        <Link href={src} download>
                            Download the file
                        </Link>
                    </MessageBar>
                </div>
            ) : (
                <div>
                    <IconButton
                        className={styles.downloadButton}
                        style={{ color: "black" }}
                        iconProps={{ iconName: "Save" }}
                        title="Save"
                        ariaLabel="Save"
                        href={src}
                        download
                    />
                    <MarkdownPreview
                        className={`${styles.markdown} ${styles.markdownViewer}`}
                        source={markdownContent}
                        rehypePlugins={[[rehypeAnchorOnClick]]}
                    />
                </div>
            )}
        </div>
    );
};
