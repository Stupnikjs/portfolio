import  Loader  from './components/Loader';
import { useState, useEffect } from 'react';
import Headeur from './layout/Headeur'
import LinkShape from './components/LinkShape';



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
            <main className='main'>
            <div className='intro'>
                <p>Bonjour, je m appelle </p>
                <h1><strong>Nicolas,</strong> Boudier </h1>
                <p>Developpeur <strong className='strong'>Javascript</strong> </p>
                <p> Fort d une experience atypique, j aspire à developper mes competences en participant a des projets </p>
            </div>
            <section className='section'> Passioné par le developpement, j étudie toutes les propositions, </section>
            <button className='contactButton'>contactez moi</button>
            <LinkShape></LinkShape>
            </main>

        </div>
    ) 

};
  
 