import  Loader  from './components/Loader';
import { useState, useEffect } from 'react';
import Headeur from './components/Headeur'

import Intro from './components/Intro';
import Paragraphe from './components/Paragraphe';
import Vertical from './components/Vertical';
import Link from 'next/link';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {faTwitter, faLinkedin, faGithub} from '@fortawesome/free-brands-svg-icons'

export default function Home() {

    const [loader, setLoader] = useState(true); 
 
 
useEffect(() => {
    
    setTimeout(() => {
        setLoader( loader => false)
    }, 2000) 
}, []); 

    return loader ? ( <Loader></Loader>) : (
        <div className={"home"} >
            <Headeur></Headeur>
            <Intro></Intro>
            <Paragraphe> Passioné par le developpement, je suis ouvert à toutes les propositions, contactez moi </Paragraphe>
            <Vertical id="email"> n.boudier.ph@gmail.com </Vertical>
            <Vertical id="media"> 
               <Link href="https://twitter.com/BoudierDev"><FontAwesomeIcon icon={faTwitter}></FontAwesomeIcon></Link> 
               <Link href="https://github.com/Stupnikjs"><FontAwesomeIcon icon={faGithub}></FontAwesomeIcon></Link> 
                <Link href="https://github.com/Stupnikjs"><FontAwesomeIcon icon={faLinkedin}></FontAwesomeIcon></Link>
             </Vertical>      


            <div>  </div>
        </div>
    ) 

};
  
 