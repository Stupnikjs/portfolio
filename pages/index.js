import  Loader  from './components/Loader';
import { useState, useEffect } from 'react';
import Image from 'next/image';
import Headeur from './layout/Headeur'
import LinkShape from './components/LinkShape';
import imgBg from "../public/images/bg.jpg"


export default function Home() {

    const [loader, setLoader] = useState(true); 
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
        
        setTimeout(() => {
            setLoader( loader => false)
        }, 2000) 

        return () => {
            window.removeEventListener("scroll", scrollHandler, { passive: true });
         }

    }, [scrollTop, scrollY]); 

    return loader ? ( <Loader></Loader>) : (
        <div className={"home"} >
            <Headeur scrolled={scrolled} ></Headeur>
            <main className='main'>
                <div className='intro'> 
                    
                    <h2>{"Bonjour, je m'appelle"} </h2>
                    <h1><strong>Nicolas,</strong> Boudier </h1>
                    <p>Developpeur <strong className='strong'>Javascript</strong> </p>
                    <div className="image-container">
                        <Image className={"imageBg"} src={imgBg} alt="image-accueuil"></Image>
                    </div>
                    
                    <h2 >{" Construisons ensemble votre projet !"}</h2>
                </div>
                <section className='section'> {""}</section>
                <button className='contactButton'>contactez moi</button>
                <LinkShape></LinkShape>
            </main>

        </div>
    ) 

};
  
 