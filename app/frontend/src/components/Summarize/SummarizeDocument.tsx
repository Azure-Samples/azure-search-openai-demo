import styles from "./Summarize.module.css";

interface Props {
    id: string;
    onRemove: () => void;
}

const SummarizeDocument = ({ id, onRemove }: Props) => {
    const url = "/content/" + id;
    return <iframe className={styles.frame} title="Citation" src={url} width="100%" height="100%" frameBorder="0" />;
};
export default SummarizeDocument;
