import  Loader  from './components/Loader';
import { useState, useEffect } from 'react';
import Headeur from './layout/Headeur'
import Intro from './layout/Intro';
import Vertical from './layout/Vertical';
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
            <p> Passioné par le developpement, j étudie toutes les propositions,  </p>
            <button className='contactButton'>contactez moi</button>
            <Vertical id="email"> n.boudier.ph@gmail.com </Vertical>
            <Vertical id="media"> 
               <Link href="https://twitter.com/BoudierDev"><FontAwesomeIcon icon={faTwitter}></FontAwesomeIcon></Link> 
               <Link href="https://github.com/Stupnikjs"><FontAwesomeIcon icon={faGithub}></FontAwesomeIcon></Link> 
                <Link href="https://github.com/Stupnikjs"><FontAwesomeIcon icon={faLinkedin}></FontAwesomeIcon></Link>
             </Vertical>      
        </div>
    ) 

};
  
 