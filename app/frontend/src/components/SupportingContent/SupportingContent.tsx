import { parseSupportingContentItem } from "./SupportingContentParser";

import styles from "./SupportingContent.module.css";

interface WebPage {
    id: string;
    name: string;
    url: string;
    displayUrl: string;
    dateLastCrawled: string;
    language: string;
    snippet?: string;
    isFamilyFriendly?: boolean;
    siteName?: string;
}

interface Props {
    supportingContent: string[] | { text: string[]; images?: string[]; web_search?: WebPage[] };
}

export const SupportingContent = ({ supportingContent }: Props) => {
    const textItems = Array.isArray(supportingContent) ? supportingContent : supportingContent.text;
    const imageItems = !Array.isArray(supportingContent) ? supportingContent?.images : [];
    const webSearchItems = !Array.isArray(supportingContent) ? supportingContent?.web_search : [];
    return (
        <ul className={styles.supportingContentNavList}>
            {textItems.map((c, ind) => {
                const parsed = parseSupportingContentItem(c);
                return (
                    <li className={styles.supportingContentItem} key={`supporting-content-text-${ind}`}>
                        <h4 className={styles.supportingContentItemHeader}>{parsed.title}</h4>
                        <p className={styles.supportingContentItemText} dangerouslySetInnerHTML={{ __html: parsed.content }} />
                    </li>
                );
            })}
            {imageItems?.map((img, ind) => {
                return (
                    <li className={styles.supportingContentItem} key={`supporting-content-image-${ind}`}>
                        <img className={styles.supportingContentItemImage} src={img} />
                    </li>
                );
            })}
            {webSearchItems?.map((webPage, ind) => {
                return (
                    <li className={styles.supportingContentItem} key={`supporting-content-web-search-${ind}`}>
                        <h4 className={styles.supportingContentItemHeader}>{webPage.name}</h4>
                        <a className={styles.supportingContentItemText} href={webPage.url} target="_blank" rel="noreferrer">
                            {webPage.url}
                        </a>
                        <p className={styles.supportingContentItemText}>{webPage.snippet}</p>
                    </li>
                );
            })}
        </ul>
    );
};
