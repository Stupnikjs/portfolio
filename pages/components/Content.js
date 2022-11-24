import React from 'react';
import Vertical from './Vertical';
import Intro from './Intro';
import Link from 'next/link';
import Paragraphe from './Paragraphe';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {faTwitter, faLinkedin, faGithub} from '@fortawesome/free-brands-svg-icons'


const Content = () => {
    return (
        <div className='content'>
            
            <Intro></Intro>
            <Paragraphe> Passioné par le developpement, je suis ouvert à toutes les propositions, contactez moi </Paragraphe>
            <Vertical id="email"> n.boudier.ph@gmail.com </Vertical>
            <Vertical id="media"> 
               <Link href="https://twitter.com/BoudierDev"><FontAwesomeIcon icon={faTwitter}></FontAwesomeIcon></Link> 
               <Link href="https://github.com/Stupnikjs"><FontAwesomeIcon icon={faGithub}></FontAwesomeIcon></Link> 
                <Link href="https://github.com/Stupnikjs"><FontAwesomeIcon icon={faLinkedin}></FontAwesomeIcon></Link>
             </Vertical>      
        </div>
    );
};

export default Content;