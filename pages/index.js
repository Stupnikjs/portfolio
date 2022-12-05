import  Loader  from './components/Loader';
import { useState, useEffect } from 'react';
import Headeur from './layout/Headeur'
import Vertical from './layout/Vertical';
import StyleBar from './components/StyleBar';
import Link from 'next/link';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {faTwitter, faLinkedin, faGithub} from '@fortawesome/free-brands-svg-icons'

export default function Home() {

    const [loader, setLoader] = useState(true); 
    let elarray = new Array(11).fill(1)

    

    const returnStyle = (x, y, op) => {
        /* rotation de 90 dans le css donc inversion des x et y */
        return {
            transform: `translateX(${x}%) scaleX(0.2) translateY(${y}%)`, 
            opacity: op,
            backgroundColor: "lightblue", 
            border: "0.7px solid grey"
        }
        
    }
 
    useEffect(() => {
        
        setTimeout(() => {
            setLoader( loader => false)
        }, 2000) 
    }, []); 

    return loader ? ( <Loader></Loader>) : (
        <div className={"home"} >
            <Headeur></Headeur>
            <main className='main'>
            <div className='intro'>
                <p>Bonjour, je m appelle </p>
                <h1><strong>Nicolas,</strong> Boudier </h1>
                <p>Developpeur <strong className='strong'>Javascript</strong> </p>
                <p> Fort d une experience atypique, j aspire à developper mes competences en participant a des projets </p>
            </div>
            <section className='section'> Passioné par le developpement, j étudie toutes les propositions, </section>
            <button className='contactButton'>contactez moi</button>
            {
            
            elarray.map((element, index) => {

                return (<StyleBar key={index} style={returnStyle(index ,index,index/10)}> {element}</StyleBar>)
            })

            }
            </main>
           
            <Vertical id="email"> n.boudier.ph@gmail.com </Vertical>
            <Vertical id="media"> 
               <Link href="https://twitter.com/BoudierDev"><FontAwesomeIcon icon={faTwitter}></FontAwesomeIcon></Link> 
               <Link href="https://github.com/Stupnikjs"><FontAwesomeIcon icon={faGithub}></FontAwesomeIcon></Link> 
                <Link href="https://github.com/Stupnikjs"><FontAwesomeIcon icon={faLinkedin}></FontAwesomeIcon></Link>
             </Vertical>      
        </div>
    ) 

};
  
 