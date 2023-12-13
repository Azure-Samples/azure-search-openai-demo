import { parseSupportingContentItem } from "./SupportingContentParser";

import styles from "./SupportingContent.module.css";

interface Props {
    supportingContent: string[] | { text: string[]; images?: { url: string }[] };
}

interface SupportingItemProps {
    title: string;
    content: string;
}

export const SupportingContent = ({ supportingContent }: Props) => {
    const textItems = Array.isArray(supportingContent) ? supportingContent : supportingContent.text;
    const imageItems = !Array.isArray(supportingContent) ? supportingContent?.images : [];
    return (
        <ul className={styles.supportingContentNavList}>
            {textItems.map(c => {
                const parsed = parseSupportingContentItem(c);
                return <TextSupportingContent {...parsed} />;
            })}
            {imageItems?.map(i => {
                return <img className={styles.supportingContentItemImage} src={i.url} />;
            })}
        </ul>
    );
};

export const TextSupportingContent = ({ title, content }: SupportingItemProps) => {
    return (
        <li className={styles.supportingContentItem}>
            <h4 className={styles.supportingContentItemHeader}>{title}</h4>
            <p className={styles.supportingContentItemText} dangerouslySetInnerHTML={{ __html: content }} />
        </li>
    );
};
