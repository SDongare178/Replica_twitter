'use strict'

//import firebase
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.9.0/firebase-app.js"
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut } from "https://www.gstatic.com/firebasejs/12.9.0/firebase-auth.js" 

// web apps firebase confige
const firebaseConfig = {
    apiKey: "AIzaSyB8uT1YRuKfbrYU7GDqA0dlDtB6a2meO-o",
    authDomain: "cpa-sd3165686.firebaseapp.com",
    projectId: "cpa-sd3165686",
    storageBucket: "cpa-sd3165686.firebasestorage.app",
    messagingSenderId: "932703395064",
    appId: "1:932703395064:web:dfa5a38eddd1fc07aeef0d"
  };

  window.addEventListener("load", function() {
    const app = initializeApp(firebaseConfig)
    const auth = getAuth()
    updateUI(document.cookie)
    console.log("hello world load")

    //signup of a new user to firbase
    document.getElementById("sign-up").addEventListener('click', function() {
        const email = document.getElementById("email").value
        const password = document.getElementById("password").value

        createUserWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
            //we have created a new user
            const user = userCredential.user

            //get the id token for the user who just logged in and force a redirect 
            user.getIdToken().then((token) => {
                document.cookie = 'token=' + token + ";path=/;SameSite=Strict";
                window.location = "/";
            });
        })
        .catch((error) => {
            //issur for signup that we will drop to console
            console.log(error.code + error.message);
        })
    })
  

  document.getElementById("login").addEventListener('click', function() {
        const email = document.getElementById("email").value
        const password = document.getElementById("password").value

        signInWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
            //we have created a new user
            const user = userCredential.user;
            console.log("logged in");

            //get the id token for the user who just logged in and force a redirect 
            user.getIdToken().then((token) => {
                document.cookie = 'token=' + token + ";path=/;SameSite=Strict";
                window.location = "/";
            })
        })
        .catch((error) => {
            //issur for signup that we will drop to console
            console.log(error.code + error.message);
        });
    })
  

    //signout from firebase
    document.getElementById("sign-out").addEventListener('click', function() {
        signOut(auth)
        .then((output) => {
            //remove the ID token d=for the user and force a redirect to /
            document.cookie = "token=;path=/;SameSite=Strict";
            window.location = "/";
        })
    });
  });

  //function that will update the UI fo the user depending on if they are logged in or note by checking the passed in cookie that contains the token
  function updateUI(cookie) {
    var token = parseCookieToken(cookie);

    //if a user is logged in then disable the email password signup and login Ui elemetns and show the signout button and vice  versa
    if(token.length > 0) {
        document.getElementById("login-box").hidden = true;
        document.getElementById("sign-out").hidden = false;  
    }else{
        document.getElementById("login-box").hidden = false;
        document.getElementById("sign-out").hidden = true;
    }
  };


  //function that will take the cookie and will return the value associated with it to the caller
  function parseCookieToken(cookie) {
    //split the cookie out on the basis of the semi-colon
    var strings = cookie.split(';');

    //go throuth each string
    for(let i = 0; i < strings.length; i++){
        //split the string based on the = sign if the LHS is token then retun the RHS immediately
        var temp = strings[i].split("=");
        if (temp[0].trim() == "token")
                return temp[1];
    }

    //if we get to this point then the woken wasnt in the cookie so retun empty string
    return ""

       
  }
  