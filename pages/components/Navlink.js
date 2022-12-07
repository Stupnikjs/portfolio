
import Link from "next/link"
import { useState } from 'react';





const Navlink = ({to, children}) => {

    const [classDivLink, setClassDivLink] = useState("notdropped")
    

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
              
            </div>
        </div>
    ) 
};

export default Navlink;