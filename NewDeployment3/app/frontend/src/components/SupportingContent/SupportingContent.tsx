import { parseSupportingContentItem } from "./SupportingContentParser";

import styles from "./SupportingContent.module.css";

interface Props {
    supportingContent: string[];
}

export const SupportingContent = ({ supportingContent }: Props) => {
    return (
        <ul className={styles.supportingContentNavList}>
            {supportingContent.map((x, i) => {
                const parsed = parseSupportingContentItem(x);

                return (
                    <li className={styles.supportingContentItem}>
                        <h4 className={styles.supportingContentItemHeader}>{parsed.title}</h4>
                        <p className={styles.supportingContentItemText}>{parsed.content}</p>
                    </li>
                );
            })}
        </ul>
    );
};
