import axios from "axios";
// a function that will try to get the user's details from the app service authentication
// if the call to the /.auth/me endpoint fails, assume we are in development and return a dummy user
// from the user_details config file.
const get_auth_user_details = () => {
    var user_object = "";

    try {
        // get the user details from the /.auth/me endpoint
        let user_object = axios.get("/.auth/me").then(r => {
            return r.data[0];
        });
        // return the first user in the response
    } catch (error) {
        //if it's a 404 error, we are in development and return a dummy user
        console.log("Error getting user details from /.auth/me endpoint");
        console.log(error);
        console.log("Are we in development?");
        let user_object = import("./dummy_user.json");
    }

    console.log("User details from app service authentication");
    console.log(user_object);
    return user_object;
};

// get_auth_user_details();
