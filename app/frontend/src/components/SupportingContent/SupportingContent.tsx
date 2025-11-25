import DOMPurify from "dompurify";

import { DataPoints } from "../../api";
import { parseSupportingContentItem } from "./SupportingContentParser";

import styles from "./SupportingContent.module.css";

interface Props {
    supportingContent?: DataPoints;
}

export const SupportingContent = ({ supportingContent }: Props) => {
    const textItems = supportingContent?.text ?? [];
    const imageItems = supportingContent?.images ?? [];
    const webItems = supportingContent?.external_results_metadata ?? [];
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
                        <img className={styles.supportingContentItemImage} src={img} alt="Supporting content" />
                    </li>
                );
            })}
            {webItems.map((item, ind) => (
                <li className={styles.supportingContentItem} key={`supporting-content-web-${item.id ?? ind}`}>
                    {item.url ? (
                        <h4 className={styles.supportingContentItemHeader}>
                            <a href={item.url} target="_blank" rel="noreferrer">
                                {item.title ?? item.url}
                            </a>
                        </h4>
                    ) : (
                        <h4 className={styles.supportingContentItemHeader}>{item.title ?? "Web result"}</h4>
                    )}
                </li>
            ))}
        </ul>
    );
};
