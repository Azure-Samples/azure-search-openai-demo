import styles from "./UserChatMessage.module.css";

interface Props {
    message: string;
}

export const UserChatMessage = ({ message }: Props) => {
    // // check if message is a blob url
    // const isBlob = message.startsWith("blob:");
    // if (isBlob) {
    //     return (
    //         <div className={styles.container}>
    //             <img src={message} alt="User uploaded image" className={styles.imagePreview} />
    //         </div>
    //     );
    // }

    const isBase64 = message.startsWith("data:image");
    if (isBase64) {
        return (
            <div className={styles.container}>
                <img src={message} alt="User uploaded image" className={styles.imagePreview} />
            </div>
        );
    }

    return (
        <div className={styles.container}>
            <div className={styles.message}>{message}</div>
        </div>
    );
};
