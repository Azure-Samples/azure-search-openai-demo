interface User {
    uuid: string;
    emailAddress: string;
    firstName: string;
    lastName: string;
    password?: string;
    initialPasswordChanged: boolean | null;
    projectName?: string;
    projectID?: string;
    projectRole?: string;
}
interface NewUser {
    uuid: string;
    emailAddress: string;
    projectRole: string;
    projectID: string;
}
