type firstNameCell = {
    label: string;
    icon: string | JSX.Element;
};
type editCell = {
    label: string;
    icon: string | JSX.Element;
};

type Item = {
    projectId: string;
    firstName: firstNameCell;
    lastName: string;
    emailAddress: string;
    projectRole: string;
    initialPasswordChanged: string;
    edit: editCell;
};
