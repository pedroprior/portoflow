import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { INICIO_POR_PAPEL, RotaProtegida } from './components/RotaProtegida';
import { useAuth } from './contexts/AuthContext';
import Agendamentos from './pages/Agendamentos';
import Agendar from './pages/Agendar';
import Cadastros from './pages/Cadastros';
import Containers from './pages/Containers';
import { Cadastro, Login } from './pages/Entrada';
import Patio from './pages/Patio';
import Perfil from './pages/Perfil';
import Portao from './pages/Portao';

const EQUIPE = ['operador', 'admin'];

function Inicio() {
  const { usuario } = useAuth();
  return <Navigate to={INICIO_POR_PAPEL[usuario.papel] ?? '/perfil'} replace />;
}

function Protegida({ papeis, children }) {
  return <RotaProtegida papeis={papeis}>{children}</RotaProtegida>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/entrar" element={<Login />} />
      <Route path="/cadastro" element={<Cadastro />} />
      <Route
        element={
          <RotaProtegida>
            <Layout />
          </RotaProtegida>
        }
      >
        <Route index element={<Inicio />} />
        <Route path="portao" element={<Protegida papeis={EQUIPE}><Portao /></Protegida>} />
        <Route path="patio" element={<Protegida papeis={EQUIPE}><Patio /></Protegida>} />
        <Route path="containers" element={<Protegida papeis={EQUIPE}><Containers /></Protegida>} />
        <Route path="agendamentos" element={<Protegida papeis={EQUIPE}><Agendamentos /></Protegida>} />
        <Route path="cadastros" element={<Protegida papeis={['admin']}><Cadastros /></Protegida>} />
        <Route path="meus-containers" element={<Protegida papeis={['externo']}><Containers /></Protegida>} />
        <Route path="agendar" element={<Protegida papeis={['externo']}><Agendar /></Protegida>} />
        <Route path="meus-agendamentos" element={<Protegida papeis={['externo']}><Agendamentos /></Protegida>} />
        <Route path="perfil" element={<Perfil />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
