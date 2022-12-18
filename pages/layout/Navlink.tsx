
import Link from "next/link"
import { useEffect, useState } from 'react';
import styles from "./navlink.module.css"

/**/
interface navlink {
    text:  string, 
    link:  string
}
type Props = {
    to: string, 
    children : string, 
    items: navlink[], 
    current: string, 
}

const Navlink = ({to, children, items, current}: Props) => {

    const [classDivLink, setClassDivLink] = useState("notdropped")
    const [active , setActive] = useState(false)

    const droppedHandler = (e: any) => {

        e.preventDefault()
        if (items) setClassDivLink("dropped")
    }

    const outDiv = (e: any) =>{
        e.preventDefault()
        setClassDivLink("notdropped")
    }

    useEffect(() => {
        if(to.substring(1) === current) setActive(true)
        else setActive(false)
    }, [current, to])


    return (
        
        <nav className={styles["divLink"]} onMouseOver={droppedHandler} onMouseOut={outDiv} >
            <div className={styles["fontlinkcontainer"]} >
                <Link href={to}  className={styles["classnavlink"]}>
                    <h2  >{children !== undefined ? children.toUpperCase(): ""}</h2>
                    <div className={active ? styles["active-link"]: styles['not-active-link']}></div>
                </Link>
            </div>
            <div className={styles[classDivLink]}>
              {items ? items.map((element,index) => {
                return (<Link className={styles.navitem} href={element.link ? element.link : ""} key={index}>{element.text}</Link>)
              }):""}
            </div>
        </nav>
    ) 
};

export default Navlink;