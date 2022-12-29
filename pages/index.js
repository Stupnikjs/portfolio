
import  React, { useState, useEffect } from 'react';

import {Playfair_Display} from '@next/font/google'; 
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faJsSquare } from '@fortawesome/free-brands-svg-icons';
import Prolink from "../components/Prolink"


const playfair = Playfair_Display({ weight:"400", subsets: ['latin']})



export default function Home() {


    useEffect(() => {
   
    }, []); 

    return (
        <div className={playfair.className}>
            <main className="main-container">
                <aside className='left-side'>
                    <Prolink></Prolink>
                </aside>
                <div className="cards-div">
                    <div className="index-card">
                        <h1> Bonjour, </h1>
                        <h2> Bienvenue sur mon Portfolio.</h2>
                        <p>Je m'appelle Nicolas Boudier </p>
                        <p> Je suis developpeur Web autodidacte <FontAwesomeIcon icon={faJsSquare}></FontAwesomeIcon> </p>
                    </div>
                    <div className="index-card">
                        <h1> Bonjour, </h1>
                        <h2> Bienvenue sur mon Portfolio.</h2>
                        <p>Je m'appelle Nicolas Boudier </p>
                        <p> Je suis developpeur Web autodidacte <FontAwesomeIcon icon={faJsSquare}></FontAwesomeIcon> </p>
                    </div>
                    <div className="index-card">
                        <h1> Bonjour, </h1>
                        <h2> Bienvenue sur mon Portfolio.</h2>
                        <p>Je m'appelle Nicolas Boudier </p>
                        <p> Je suis developpeur Web autodidacte <FontAwesomeIcon icon={faJsSquare}></FontAwesomeIcon> </p>
                    </div>
                    <div className="index-card">
                        <h1> Bonjour, </h1>
                        <h2> Bienvenue sur mon Portfolio.</h2>
                        <p>Je m'appelle Nicolas Boudier </p>
                        <p> Je suis developpeur Web autodidacte <FontAwesomeIcon icon={faJsSquare}></FontAwesomeIcon> </p>
                    </div>
                </div>
                
            </main>
        </div>
    ) 

};
  
 