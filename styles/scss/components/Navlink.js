
import Link from "next/link"
import { useState } from 'react';


/**/


const Navlink = ({to, children, items}) => {

    const [classDivLink, setClassDivLink] = useState("notdropped")
    

    /* coder le cancel du dropdown si dropdown d'un autre  */
    /* quand on click sur le bouton:  
    - check si aucun autre drop est ouvert donc navclick === 0 


    */

    const droppedHandler = (e) => {

        e.preventDefault()
        setClassDivLink("dropped")
    }

    const outDiv = (e) =>{
        e.preventDefault()
        setClassDivLink("notdropped")
    }

    

    return (
        
        <div className="divLink" onMouseOver={droppedHandler} onMouseOut={outDiv} >
            <div className='fontlinkcontainer' >
                <Link href={to}  className="classnavlink">
                    <h2>{children !== undefined ? children.toUpperCase(): ""}</h2>
                </Link>
            </div>
            <div className={classDivLink}>
              {items ? items.map((element,index) => {
                return (<li key={index}>{element}</li>)
              }):""}
            </div>
        </div>
    ) 
};

export default Navlink;