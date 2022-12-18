
import { useState, useEffect } from 'react';
import Image from 'next/image';
import Headeur from './layout/Headeur'
import Footer from "./layout/Footer"
import ProLink from "../components/ProLink"
import {Playfair_Display} from '@next/font/google'; 

const playfair = Playfair_Display({ weight:"400", subsets: ['latin']})

export default function Home() {

   
    const [scrollY, setScrollY] = useState(0); 
    const [scrolled, setScrolled] = useState(false)
    const [scrollTop, setScrollTop] = useState(false)
    const [displayArrow, setDisplayArrow] = useState(false)

    const scrollHandler= (e) => {

        const {scrollY} = window;
        const windowHeight = window.innerHeight 
        setScrollY(scrollY)
        if (scrollY > windowHeight) setDisplayArrow(true)
        else setDisplayArrow(false)
    }



    useEffect(() => {
      
        if (scrollY > 0) setScrolled(true)
        if (scrollY === 0) setScrolled(false)

        window.addEventListener("scroll", scrollHandler, {passive: true})
        if (scrollTop){ 
            window.scrollTo({ top: 0, behavior:"smooth"})
            setScrollTop(false)
        }
        
        

        return () => {
            window.removeEventListener("scroll", scrollHandler, { passive: true });
         }

    }, [scrollTop, scrollY]); 

    return (
        <div className={playfair.className}>
            <Headeur scrolled={scrolled} ></Headeur>
            <main className='main_index'>
                <div className='index_presentation'> 
                    <h2> Bonjour, je m'appelle </h2>
                    <h1><strong>Nicolas,</strong> Boudier </h1>
                    <p>Developpeur <strong className='strong'>Javascript</strong> </p>
                    
                    <h2 > Construisons ensemble votre projet !</h2>
                </div>
                <button className='contact_button'>contactez moi</button>
                <ProLink></ProLink>
            </main>
            <Footer></Footer>
        </div>
    ) 

};
  
 