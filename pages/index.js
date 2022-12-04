import  Loader  from './components/Loader';
import { useState, useEffect } from 'react';
import Headeur from './layout/Headeur'
import Intro from './layout/Intro';
import Vertical from './layout/Vertical';
import StyleBar from './components/styleBar';
import Link from 'next/link';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {faTwitter, faLinkedin, faGithub} from '@fortawesome/free-brands-svg-icons'

export default function Home() {

    const [loader, setLoader] = useState(true); 
    let elarray = new Array(5).fill(1)

    

    const returnStyle = (x, y, op) => {
        /* rotation de 90 dans le css donc inversion des x et y */
        return {
            transform: `translateX(${-15*x +5 }%) scaleX(0.5) translateY(${-20*y}%)`, 
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
            <Intro></Intro>
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
  
 