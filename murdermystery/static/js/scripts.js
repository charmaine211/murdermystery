function login(){
    let username = document.querySelector("#username").value;
    let password = document.querySelector("#password").value;

    if (username ==='' || password === '')
    {
        alert("Please provide a username and password");
        return false;
    }
}

function register(){
    let username = document.querySelector("#username").value;
    let password = document.querySelector("#password").value;
    let confirmation =  document.querySelector("#confirmation").value;

    var errors = [];

    if (username ==='' || email === '' || password === '' || confirmation === ''){
        alert("Please provide a username, password and confirm your password");
        return false;
    }
    if (password.length < 8) {
        errors.push("Your password must be at least 8 characters");
    }
    if (password.search(/[a-z]/i) < 0) {
        errors.push("Your password must contain at least one letter.");
    }
    if (password.search(/[A-Z]/) < 0) {
        errors.push("Your password must contain at least one uppercase letter.");
    }
    if (password.search(/[0-9]/) < 0) {
        errors.push("Your password must contain at least one digit.");
    }
    if (password.search(/['!', '@', '#', '$', '%', '^', '\&', '*', '(', ')', '<', '>', '[', '\]', '{','}','|',';',':','§','±','€', '\\', '\'', '\"', '\_']/) < 0) {
        errors.push("Your password must contain at least one special character.");
    }
    if (password !== confirmation) {
        errors.push("Your password and password confirmation don't match.");
    }
    if (errors.length > 0) {
        alert(errors.join("\n"));
        return false;
    }
}

// Show and hide text when dropdown menu is selected
function display(){
    var e = document.getElementById("dropDownId");
    var index = e.selectedIndex;
    if(index==0){
        document.getElementById("first").style.display = 'block';
        document.getElementById("second").style.display = 'none';
    }
    else if(index==1){
        document.getElementById("first").style.display = 'none';
        document.getElementById("second").style.display = 'block';
    }
}

function create_a_new_team(){

    "Make sure everything is filled out"

    "Make sure there are no special chars in new teamname"

}