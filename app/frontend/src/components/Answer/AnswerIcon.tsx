import { Sparkle28Filled } from "@fluentui/react-icons";
import avImage from "./dimalbl.png";
import styles from "./Answer.module.css";
export const AnswerIcon = () => {
    return <img className={styles.avatar} src={avImage} alt="Avatar Asistent" />;
    // <Sparkle28Filled primaryFill={"rgba(115, 118, 225, 1)"} aria-hidden="true" aria-label="Answer logo" />;
};
