import { parseSupportingContentItem } from "../SupportingContent/SupportingContentParser";

import styles from "./AnalysisPanel.module.css";

interface Props {
    question: string;
    answer: string;
    supportingContent: string[] | { text: string[]; images?: { url: string }[] };
}

interface SupportingItemProps {
    title: string;
    content: string;
}

/*
Evaluations that we can do:
- Context Precision: Question & Context
- Answer Relevance: Question & Answer
- Faithfulness: Answer & Context
*/

export const Evaluation = ({ question, answer, supportingContent }: Props) => {
    const textItems = Array.isArray(supportingContent) ? supportingContent : supportingContent.text;
    const imageItems = !Array.isArray(supportingContent) ? supportingContent?.images : [];

    return (
        <ul>
            <li>
                <span>
                    <h2>Question</h2>
                </span>
                {question}
            </li>
            <li>
                <span>
                    <h2>Answer</h2>
                </span>{" "}
                {answer}
            </li>
            <li>
                <span>
                    <h2>Contexts</h2>
                </span>
            </li>
            <ul className={styles.supportingContentNavList}>
                {textItems.map(c => {
                    const parsed = parseSupportingContentItem(c);
                    return <TextSupportingContent {...parsed} />;
                })}
                {imageItems?.map(i => {
                    return <img className={styles.supportingContentItemImage} src={i.url} />;
                })}
            </ul>
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
