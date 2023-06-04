import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "Create a one page summary of APEX tools.",
        value: "Create a detailed one pager summary for credit hedge fund analyst for apex tool using 2023 Q1 and other latest data and listing sources. Looks like: Company overview: Overview here Capital Structure: Capital Structure here and list the amount of each item. For Term Loan and Revolving Credit Facility look at Apex Tool Group Q1 2023 Financial Capitalization & Liquidity: Metrics here and show trends Financial Results and Estimates: results here and include last 4 quarters Positive Trends: Trends here Negative Trends and Risks: Trends and risk here and elaborate more on the risk factors and list numbers Loan Covenants: Covenants here and list important covenants to credit analyst. List numeric amount of threshold and current number."
    },
    { text: "What drives Apex Tool's EBITDA change in the last 4 quarters?", value: "What drives Apex Tool's EBITDA change in the last 4 quarters? Give a detailed response that a credit analyst at a hedge fund would want." },
    { text: "Show calculation of Apex Tool's adjusted EBITDA for Q1 2023.", value: "Show calculation of Apex Tool's adjusted EBITDA for Q1 2023, Give a detailed response that a credit analyst at a hedge fund would want." }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {EXAMPLES.map((x, i) => (
                <li key={i}>
                    <Example text={x.text} value={x.value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
